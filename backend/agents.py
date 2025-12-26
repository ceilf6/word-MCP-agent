"""
AgentScope 多智能体协作模块

实现三个协作 Agent：
1. StructurizerAgent - 将用户非结构化输入转为结构化数据
2. WriterAgent - 根据结构化数据创作文档
3. ReviewerAgent - 对文档评分并决定是否重新生成

工作流程：
用户输入 → 结构化Agent → 创作Agent → 评分Agent → [评分>=7] → 输出
                                        ↓ [评分<7]
                                      重新创作（最多3轮）
"""

import json
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# AgentScope 导入（如果已安装）
try:
    import agentscope
    from agentscope.agents import AgentBase, ReActAgent
    from agentscope.message import Msg
    from agentscope.pipelines import SequentialPipeline
    AGENTSCOPE_AVAILABLE = True
except ImportError:
    AGENTSCOPE_AVAILABLE = False
    print("AgentScope 未安装，使用本地模拟实现")


# ==================== 数据结构 ====================

@dataclass
class StructuredTask:
    """结构化任务数据"""
    intent: str  # 意图：create, update, format 等
    document_name: Optional[str] = None
    title: Optional[str] = None
    content_requirements: List[str] = field(default_factory=list)
    style_requirements: Dict[str, Any] = field(default_factory=dict)
    include_table: bool = False
    table_data: Optional[List[List[str]]] = None
    include_image: bool = False
    image_query: Optional[str] = None
    additional_notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "document_name": self.document_name,
            "title": self.title,
            "content_requirements": self.content_requirements,
            "style_requirements": self.style_requirements,
            "include_table": self.include_table,
            "table_data": self.table_data,
            "include_image": self.include_image,
            "image_query": self.image_query,
            "additional_notes": self.additional_notes
        }


@dataclass
class DocumentDraft:
    """文档草稿"""
    filename: str
    title: str
    content: str
    tables: List[List[List[str]]] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ReviewResult:
    """评审结果"""
    score: int  # 1-10
    passed: bool  # score >= threshold
    feedback: str
    improvement_suggestions: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)


@dataclass
class CoTThinking:
    """Chain of Thought 思考过程"""
    # 总结分析
    task_summary: str  # 原始任务总结
    draft_summary: str  # 文档草稿总结
    
    # 关系变化分析
    requirement_coverage: Dict[str, bool] = field(default_factory=dict)  # 需求覆盖情况
    intent_alignment: str = ""  # 意图对齐程度分析
    style_consistency: str = ""  # 风格一致性分析
    
    # 指令一致性分析
    instruction_analysis: str = ""  # 指令执行分析
    deviation_points: List[str] = field(default_factory=list)  # 偏离点
    alignment_score: float = 0.0  # 对齐得分 (0-1)
    
    # 深度思考
    reasoning_chain: List[str] = field(default_factory=list)  # 推理链条
    key_observations: List[str] = field(default_factory=list)  # 关键观察
    
    def to_dict(self) -> dict:
        return {
            "task_summary": self.task_summary,
            "draft_summary": self.draft_summary,
            "requirement_coverage": self.requirement_coverage,
            "intent_alignment": self.intent_alignment,
            "style_consistency": self.style_consistency,
            "instruction_analysis": self.instruction_analysis,
            "deviation_points": self.deviation_points,
            "alignment_score": self.alignment_score,
            "reasoning_chain": self.reasoning_chain,
            "key_observations": self.key_observations
        }


@dataclass
class DimensionScore:
    """多维度评分"""
    content_quality: float = 0.0  # 内容质量 (1-10)
    structure_organization: float = 0.0  # 结构组织 (1-10)
    language_expression: float = 0.0  # 语言表达 (1-10)
    format_standard: float = 0.0  # 格式规范 (1-10)
    requirement_match: float = 0.0  # 需求匹配度 (1-10)
    
    # 各维度权重
    weights: Dict[str, float] = field(default_factory=lambda: {
        "content_quality": 0.30,
        "structure_organization": 0.20,
        "language_expression": 0.20,
        "format_standard": 0.10,
        "requirement_match": 0.20
    })
    
    # 各维度详细评价
    dimension_feedback: Dict[str, str] = field(default_factory=dict)
    
    def calculate_weighted_score(self) -> float:
        """计算加权总分"""
        total = (
            self.content_quality * self.weights["content_quality"] +
            self.structure_organization * self.weights["structure_organization"] +
            self.language_expression * self.weights["language_expression"] +
            self.format_standard * self.weights["format_standard"] +
            self.requirement_match * self.weights["requirement_match"]
        )
        return round(total, 2)
    
    def to_dict(self) -> dict:
        return {
            "content_quality": self.content_quality,
            "structure_organization": self.structure_organization,
            "language_expression": self.language_expression,
            "format_standard": self.format_standard,
            "requirement_match": self.requirement_match,
            "weighted_total": self.calculate_weighted_score(),
            "dimension_feedback": self.dimension_feedback
        }


@dataclass
class AgentFeedback:
    """发送给其他 Agent 的反馈"""
    target_agent: str  # 目标 Agent: "structurizer" | "writer"
    priority: str  # 优先级: "high" | "medium" | "low"
    feedback_type: str  # 反馈类型: "improvement" | "warning" | "suggestion"
    message: str  # 反馈内容
    specific_points: List[str] = field(default_factory=list)  # 具体要点
    action_items: List[str] = field(default_factory=list)  # 建议行动
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文信息
    
    def to_dict(self) -> dict:
        return {
            "target_agent": self.target_agent,
            "priority": self.priority,
            "feedback_type": self.feedback_type,
            "message": self.message,
            "specific_points": self.specific_points,
            "action_items": self.action_items,
            "context": self.context
        }


@dataclass
class EnhancedReviewResult:
    """增强版评审结果"""
    # 基础评审信息
    score: int  # 最终评分 1-10
    passed: bool  # 是否通过
    
    # CoT 思考过程
    cot_thinking: CoTThinking = None
    
    # 多维度评分
    dimension_scores: DimensionScore = None
    
    # 综合反馈
    overall_feedback: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    # 给其他 Agent 的反馈
    agent_feedbacks: List[AgentFeedback] = field(default_factory=list)
    
    # 元信息
    review_timestamp: str = ""
    review_iteration: int = 0
    
    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "passed": self.passed,
            "cot_thinking": self.cot_thinking.to_dict() if self.cot_thinking else None,
            "dimension_scores": self.dimension_scores.to_dict() if self.dimension_scores else None,
            "overall_feedback": self.overall_feedback,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "improvement_suggestions": self.improvement_suggestions,
            "agent_feedbacks": [f.to_dict() for f in self.agent_feedbacks],
            "review_timestamp": self.review_timestamp,
            "review_iteration": self.review_iteration
        }
    
    def get_feedback_for_agent(self, agent_name: str) -> List[AgentFeedback]:
        """获取发送给特定 Agent 的反馈"""
        return [f for f in self.agent_feedbacks if f.target_agent == agent_name]


# ==================== Agent 基类（本地实现）====================

class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(self, name: str, system_prompt: str, model_config: Optional[Dict] = None):
        self.name = name
        self.system_prompt = system_prompt
        self.model_config = model_config or {}
        self.history: List[Dict] = []
    
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """处理输入，返回输出"""
        pass
    
    def _call_llm(self, prompt: str) -> str:
        """调用 LLM（需要实现具体的 API 调用）"""
        # 这里可以接入 OpenAI、Gemini、本地模型等
        # 返回模拟结果用于演示
        return f"[{self.name}] 处理完成"


# ==================== 结构化 Agent ====================

class StructurizerAgent(BaseAgent):
    """
    结构化 Agent：将用户非结构化输入转为结构化任务数据
    
    职责：
    - 识别用户意图（创建/修改/删除文档等）
    - 提取关键参数（文件名、标题、内容要求）
    - 识别特殊需求（表格、图片、格式要求）
    - 标记缺失信息，生成澄清问题
    """
    
    def __init__(self, model_config: Optional[Dict] = None):
        system_prompt = """你是一个输入结构化专家。你的任务是将用户的非结构化请求转换为结构化的任务数据。

## 输出格式（JSON）
{
    "intent": "create|update|delete|format|add_table|insert_image|search",
    "document_name": "文件名或null",
    "title": "文档标题或null", 
    "content_requirements": ["内容要求1", "内容要求2"],
    "style_requirements": {"tone": "正式/轻松", "length": "短/中/长"},
    "include_table": true/false,
    "table_data": [[表格数据]] 或 null,
    "include_image": true/false,
    "image_query": "图片搜索关键词或null",
    "additional_notes": "其他备注",
    "missing_info": ["缺失的信息"],
    "clarification_questions": ["需要向用户确认的问题"]
}

## 规则
1. 不要假设任何未明确提供的信息
2. 缺失关键信息时，在 missing_info 中列出
3. 有歧义时，在 clarification_questions 中提问
4. 只输出 JSON，不要其他解释"""
        
        super().__init__("Structurizer", system_prompt, model_config)
    
    def process(self, user_input: str) -> Tuple[StructuredTask, List[str]]:
        """
        处理用户输入，返回结构化任务和需要澄清的问题
        
        Args:
            user_input: 用户的自然语言输入
            
        Returns:
            (StructuredTask, clarification_questions)
        """
        # 构建 prompt
        prompt = f"{self.system_prompt}\n\n用户输入：{user_input}"
        
        # 调用 LLM 或使用规则解析
        result = self._parse_input(user_input)
        
        return result
    
    def _parse_input(self, text: str) -> Tuple[StructuredTask, List[str]]:
        """使用规则解析输入（可替换为 LLM 调用）"""
        import re
        
        task = StructuredTask(intent="create")
        questions = []
        
        # 识别意图
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["创建", "新建", "生成", "写", "create"]):
            task.intent = "create"
        elif any(kw in text_lower for kw in ["修改", "更新", "追加", "update"]):
            task.intent = "update"
        elif any(kw in text_lower for kw in ["删除", "移除", "delete"]):
            task.intent = "delete"
        elif any(kw in text_lower for kw in ["格式", "加粗", "format"]):
            task.intent = "format"
        
        # 提取文件名
        match = re.search(r'[\w\u4e00-\u9fff_-]+\.docx', text)
        if match:
            task.document_name = match.group()
        else:
            match = re.search(r'(?:文档|文件|叫|名为|命名)\s*[：:]*\s*["\']?([^"\'，。\s]+)', text)
            if match:
                task.document_name = match.group(1)
            else:
                questions.append("请问文档要叫什么名字？")
        
        # 提取标题
        match = re.search(r'标题[：:为是]\s*["\']?([^"\'，。\n]+)', text)
        if match:
            task.title = match.group(1).strip()
        
        # 检测表格需求
        if any(kw in text for kw in ["表格", "table", "列表"]):
            task.include_table = True
            questions.append("请提供表格的具体数据内容")
        
        # 检测图片需求
        if any(kw in text for kw in ["图片", "图像", "image", "picture"]):
            task.include_image = True
            match = re.search(r'(?:关于|有关|展示)\s*([^的]+)\s*的?\s*图', text)
            if match:
                task.image_query = match.group(1)
            else:
                questions.append("请问需要什么主题的图片？")
        
        # 提取内容要求
        content_patterns = [
            r'内容[：:包含包括有]\s*(.+?)(?:[。；]|$)',
            r'写[：:]\s*(.+?)(?:[。；]|$)',
            r'介绍\s*(.+?)(?:[。；]|$)',
        ]
        for pattern in content_patterns:
            match = re.search(pattern, text)
            if match:
                task.content_requirements.append(match.group(1).strip())
        
        # 检测风格要求
        if any(kw in text for kw in ["正式", "专业", "商务"]):
            task.style_requirements["tone"] = "formal"
        elif any(kw in text for kw in ["轻松", "活泼", "有趣"]):
            task.style_requirements["tone"] = "casual"
        
        if any(kw in text for kw in ["简短", "简洁", "brief"]):
            task.style_requirements["length"] = "short"
        elif any(kw in text for kw in ["详细", "完整", "详尽"]):
            task.style_requirements["length"] = "long"
        
        return task, questions


# ==================== 创作 Agent ====================

class WriterAgent(BaseAgent):
    """
    创作 Agent：根据结构化任务创作文档内容
    
    职责：
    - 根据内容要求生成文档正文
    - 根据风格要求调整写作风格
    - 生成表格数据（如果需要）
    - 调用工具完成文档操作
    """
    
    def __init__(self, word_tools: Dict = None, model_config: Optional[Dict] = None):
        system_prompt = """你是一个专业的文档撰写专家。你的任务是根据结构化的任务要求创作高质量的文档内容。

## 写作原则
1. 内容要切题、准确、有价值
2. 结构清晰，段落分明
3. 语言流畅，符合指定的风格要求
4. 适当使用标题、列表等格式增强可读性

## 输出要求
直接输出文档内容，使用 Markdown 格式标记标题和列表。"""
        
        super().__init__("Writer", system_prompt, model_config)
        self.word_tools = word_tools or {}
    
    def process(self, task: StructuredTask) -> DocumentDraft:
        """
        根据结构化任务创作文档
        
        Args:
            task: 结构化任务数据
            
        Returns:
            DocumentDraft 文档草稿
        """
        # 生成文档内容
        content = self._generate_content(task)
        
        # 创建草稿
        draft = DocumentDraft(
            filename=task.document_name or f"document_{self._timestamp()}.docx",
            title=task.title or "未命名文档",
            content=content,
            metadata={
                "intent": task.intent,
                "style": task.style_requirements
            }
        )
        
        # 如果需要表格
        if task.include_table and task.table_data:
            draft.tables.append(task.table_data)
        
        return draft
    
    def _generate_content(self, task: StructuredTask) -> str:
        """生成文档内容（可替换为 LLM 调用）"""
        # 这里是模板生成，实际使用时应调用 LLM
        content_parts = []
        
        if task.title:
            content_parts.append(f"# {task.title}\n")
        
        if task.content_requirements:
            content_parts.append("## 主要内容\n")
            for req in task.content_requirements:
                content_parts.append(f"{req}\n")
        
        if task.additional_notes:
            content_parts.append(f"\n{task.additional_notes}\n")
        
        return "\n".join(content_parts) if content_parts else "文档内容待补充"
    
    def _timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")


# ==================== 评审 Agent ====================

class ReviewerAgent(BaseAgent):
    """
    评审 Agent：对文档进行评分并提供反馈
    
    职责：
    - 评估文档质量（内容、结构、语言）
    - 给出 1-10 分的评分
    - 提供具体的改进建议
    - 决定是否需要重新生成
    """
    
    def __init__(self, pass_threshold: int = 7, model_config: Optional[Dict] = None):
        system_prompt = """你是一个严格的文档评审专家。你的任务是评估文档质量并提供建设性反馈。

## 评分维度（每项 1-10 分）
1. 内容质量：信息准确性、完整性、价值
2. 结构组织：逻辑性、层次感、可读性
3. 语言表达：流畅度、专业性、风格一致性
4. 格式规范：标题、段落、列表使用

## 输出格式（JSON）
{
    "scores": {
        "content": 8,
        "structure": 7,
        "language": 8,
        "format": 7
    },
    "overall_score": 7.5,
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"],
    "suggestions": ["建议1", "建议2"],
    "verdict": "pass" 或 "revise"
}"""
        
        super().__init__("Reviewer", system_prompt, model_config)
        self.pass_threshold = pass_threshold
        self.review_history: List[EnhancedReviewResult] = []  # 评审历史
    
    def process(self, draft: DocumentDraft, task: StructuredTask) -> ReviewResult:
        """
        评审文档草稿（基础版本，保持向后兼容）
        
        Args:
            draft: 文档草稿
            task: 原始任务（用于对比检查）
            
        Returns:
            ReviewResult 评审结果
        """
        # 评估文档
        score, feedback, suggestions, strengths = self._evaluate(draft, task)
        
        return ReviewResult(
            score=score,
            passed=score >= self.pass_threshold,
            feedback=feedback,
            improvement_suggestions=suggestions,
            strengths=strengths
        )
    
    def process_enhanced(
        self, 
        draft: DocumentDraft, 
        task: StructuredTask,
        iteration: int = 1,
        previous_review: Optional['EnhancedReviewResult'] = None
    ) -> EnhancedReviewResult:
        """
        增强版评审处理 - 包含 CoT 思考、多维度评分和 Agent 反馈
        
        Args:
            draft: 文档草稿
            task: 原始任务
            iteration: 当前评审轮次
            previous_review: 上一轮评审结果（用于对比分析）
            
        Returns:
            EnhancedReviewResult 增强版评审结果
        """
        from datetime import datetime
        
        # Step 1: CoT 思考过程
        print("    🧠 开始 Chain of Thought 思考...")
        cot = self._perform_cot_thinking(draft, task, previous_review)
        
        # Step 2: 多维度评分
        print("    📊 进行多维度评分...")
        dimension_scores = self._calculate_dimension_scores(draft, task, cot)
        
        # Step 3: 生成综合评价
        print("    📝 生成综合评价...")
        strengths, weaknesses, suggestions = self._generate_comprehensive_feedback(
            draft, task, cot, dimension_scores
        )
        
        # Step 4: 计算最终得分
        final_score = int(round(dimension_scores.calculate_weighted_score()))
        final_score = max(1, min(10, final_score))
        
        # Step 5: 生成给其他 Agent 的反馈
        print("    💬 生成 Agent 反馈...")
        agent_feedbacks = self._generate_agent_feedbacks(
            draft, task, cot, dimension_scores, strengths, weaknesses, suggestions
        )
        
        # 构建增强版评审结果
        result = EnhancedReviewResult(
            score=final_score,
            passed=final_score >= self.pass_threshold,
            cot_thinking=cot,
            dimension_scores=dimension_scores,
            overall_feedback=self._generate_overall_feedback(final_score, cot),
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_suggestions=suggestions,
            agent_feedbacks=agent_feedbacks,
            review_timestamp=datetime.now().isoformat(),
            review_iteration=iteration
        )
        
        # 保存到评审历史
        self.review_history.append(result)
        
        return result
    
    def _perform_cot_thinking(
        self, 
        draft: DocumentDraft, 
        task: StructuredTask,
        previous_review: Optional['EnhancedReviewResult'] = None
    ) -> CoTThinking:
        """
        执行 Chain of Thought 思考过程
        
        包括：
        1. 任务和草稿总结
        2. 需求覆盖分析
        3. 意图和风格一致性检查
        4. 指令对齐分析
        """
        reasoning_chain = []
        key_observations = []
        
        # === 1. 任务总结 ===
        reasoning_chain.append("📋 分析原始任务要求...")
        task_summary = f"意图：{task.intent}，目标文档：{task.document_name or '未指定'}，标题要求：{task.title or '未指定'}"
        if task.content_requirements:
            task_summary += f"，内容要求：{len(task.content_requirements)}项"
        if task.style_requirements:
            task_summary += f"，风格要求：{task.style_requirements}"
        
        reasoning_chain.append(f"  → 任务解析完成：{task_summary[:100]}...")
        
        # === 2. 草稿总结 ===
        reasoning_chain.append("📄 分析文档草稿...")
        content_length = len(draft.content)
        has_structure = "##" in draft.content or "\n\n" in draft.content
        has_lists = "- " in draft.content or "* " in draft.content or "1. " in draft.content
        
        draft_summary = f"标题：{draft.title}，内容长度：{content_length}字符"
        if has_structure:
            draft_summary += "，有层次结构"
        if has_lists:
            draft_summary += "，包含列表"
        if draft.tables:
            draft_summary += f"，{len(draft.tables)}个表格"
        if draft.images:
            draft_summary += f"，{len(draft.images)}张图片"
        
        reasoning_chain.append(f"  → 草稿解析完成：{draft_summary}")
        
        # === 3. 需求覆盖分析 ===
        reasoning_chain.append("🔍 检查需求覆盖情况...")
        requirement_coverage = {}
        coverage_issues = []
        
        for i, req in enumerate(task.content_requirements):
            # 简单的关键词匹配（实际应用中可以使用更复杂的语义匹配）
            req_keywords = [w for w in req.split() if len(w) > 2]
            matched = any(kw.lower() in draft.content.lower() for kw in req_keywords) if req_keywords else (req.lower() in draft.content.lower())
            requirement_coverage[f"需求{i+1}: {req[:30]}..."] = matched
            
            if matched:
                key_observations.append(f"✓ 需求 '{req[:20]}...' 已覆盖")
            else:
                coverage_issues.append(f"需求 '{req[:20]}...' 未充分覆盖")
                key_observations.append(f"✗ 需求 '{req[:20]}...' 未覆盖")
        
        coverage_rate = sum(requirement_coverage.values()) / len(requirement_coverage) if requirement_coverage else 1.0
        reasoning_chain.append(f"  → 需求覆盖率：{coverage_rate*100:.1f}%")
        
        # === 4. 意图对齐分析 ===
        reasoning_chain.append("🎯 分析意图对齐程度...")
        intent_alignment = ""
        
        if task.intent == "create":
            if draft.content and len(draft.content) > 50:
                intent_alignment = "意图对齐：已成功创建文档内容"
            else:
                intent_alignment = "意图偏差：文档创建不完整，内容过少"
                key_observations.append("⚠️ 文档内容不够充实")
        elif task.intent == "update":
            intent_alignment = "意图分析：更新操作需验证改动有效性"
        elif task.intent == "format":
            intent_alignment = "意图分析：格式化操作需检查样式变化"
        else:
            intent_alignment = f"意图分析：{task.intent} 操作待验证"
        
        reasoning_chain.append(f"  → {intent_alignment}")
        
        # === 5. 风格一致性检查 ===
        reasoning_chain.append("🎨 检查风格一致性...")
        style_consistency = ""
        
        required_tone = task.style_requirements.get("tone", "")
        required_length = task.style_requirements.get("length", "")
        
        style_issues = []
        if required_tone == "formal":
            informal_markers = ["哈哈", "嘿嘿", "呢", "啦", "哦", "呀"]
            has_informal = any(m in draft.content for m in informal_markers)
            if has_informal:
                style_issues.append("发现非正式语气词汇")
            else:
                key_observations.append("✓ 语气符合正式要求")
        elif required_tone == "casual":
            key_observations.append("✓ 采用轻松语气")
        
        if required_length == "short" and content_length > 800:
            style_issues.append("内容可能过长，要求简短")
        elif required_length == "long" and content_length < 300:
            style_issues.append("内容可能过短，要求详细")
        
        if style_issues:
            style_consistency = f"风格偏差：{'; '.join(style_issues)}"
            key_observations.extend([f"⚠️ {issue}" for issue in style_issues])
        else:
            style_consistency = "风格一致：符合要求的风格规范"
        
        reasoning_chain.append(f"  → {style_consistency}")
        
        # === 6. 指令一致性分析 ===
        reasoning_chain.append("📐 分析指令执行一致性...")
        deviation_points = []
        alignment_checks = []
        
        # 检查标题是否符合要求
        if task.title:
            if task.title.lower() in draft.title.lower() or draft.title.lower() in task.title.lower():
                alignment_checks.append(True)
            else:
                deviation_points.append(f"标题不匹配：期望'{task.title}'，实际'{draft.title}'")
                alignment_checks.append(False)
        
        # 检查表格需求
        if task.include_table:
            if draft.tables:
                alignment_checks.append(True)
                key_observations.append("✓ 已包含表格")
            else:
                deviation_points.append("要求包含表格但未生成")
                alignment_checks.append(False)
        
        # 检查图片需求
        if task.include_image:
            if draft.images:
                alignment_checks.append(True)
                key_observations.append("✓ 已包含图片")
            else:
                deviation_points.append("要求包含图片但未生成")
                alignment_checks.append(False)
        
        # 计算对齐得分
        alignment_score = sum(alignment_checks) / len(alignment_checks) if alignment_checks else 1.0
        alignment_score = max(0.0, min(1.0, alignment_score))
        
        # 考虑需求覆盖率
        alignment_score = (alignment_score + coverage_rate) / 2
        
        instruction_analysis = f"指令执行分析：对齐得分 {alignment_score*100:.1f}%"
        if deviation_points:
            instruction_analysis += f"，发现 {len(deviation_points)} 个偏离点"
        else:
            instruction_analysis += "，指令执行良好"
        
        reasoning_chain.append(f"  → {instruction_analysis}")
        
        # === 7. 与上一轮对比（如果有）===
        if previous_review:
            reasoning_chain.append("📈 与上一轮评审对比...")
            prev_score = previous_review.score
            if previous_review.improvement_suggestions:
                addressed = sum(1 for s in previous_review.improvement_suggestions 
                               if any(kw in draft.content.lower() for kw in s.lower().split()[:3]))
                reasoning_chain.append(f"  → 上轮建议采纳：{addressed}/{len(previous_review.improvement_suggestions)}项")
                key_observations.append(f"📈 相比上轮，已改进 {addressed} 项建议")
        
        reasoning_chain.append("✅ CoT 思考完成")
        
        return CoTThinking(
            task_summary=task_summary,
            draft_summary=draft_summary,
            requirement_coverage=requirement_coverage,
            intent_alignment=intent_alignment,
            style_consistency=style_consistency,
            instruction_analysis=instruction_analysis,
            deviation_points=deviation_points,
            alignment_score=alignment_score,
            reasoning_chain=reasoning_chain,
            key_observations=key_observations
        )
    
    def _calculate_dimension_scores(
        self, 
        draft: DocumentDraft, 
        task: StructuredTask,
        cot: CoTThinking
    ) -> DimensionScore:
        """
        计算多维度评分
        """
        scores = DimensionScore()
        
        # === 1. 内容质量评分 ===
        content_score = 5.0
        content_feedback = []
        
        # 内容长度
        content_length = len(draft.content)
        if content_length > 1000:
            content_score += 2.0
            content_feedback.append("内容充实详尽")
        elif content_length > 500:
            content_score += 1.5
            content_feedback.append("内容较为丰富")
        elif content_length > 200:
            content_score += 0.5
            content_feedback.append("内容基本足够")
        else:
            content_score -= 1.0
            content_feedback.append("内容过于简短")
        
        # 需求覆盖
        coverage_rate = sum(cot.requirement_coverage.values()) / len(cot.requirement_coverage) if cot.requirement_coverage else 1.0
        content_score += coverage_rate * 2
        content_feedback.append(f"需求覆盖率 {coverage_rate*100:.0f}%")
        
        scores.content_quality = max(1.0, min(10.0, content_score))
        scores.dimension_feedback["content_quality"] = "；".join(content_feedback)
        
        # === 2. 结构组织评分 ===
        structure_score = 5.0
        structure_feedback = []
        
        # 标题层次
        h1_count = draft.content.count("# ")
        h2_count = draft.content.count("## ")
        h3_count = draft.content.count("### ")
        
        if h2_count > 0:
            structure_score += 1.5
            structure_feedback.append(f"有 {h2_count} 个二级标题")
        if h3_count > 0:
            structure_score += 1.0
            structure_feedback.append(f"有 {h3_count} 个三级标题")
        
        # 段落分布
        paragraphs = [p for p in draft.content.split("\n\n") if p.strip()]
        if len(paragraphs) > 5:
            structure_score += 1.5
            structure_feedback.append("段落划分合理")
        elif len(paragraphs) > 2:
            structure_score += 0.5
            structure_feedback.append("有基本段落结构")
        else:
            structure_feedback.append("段落较少，建议分段")
        
        # 列表使用
        has_lists = "- " in draft.content or "* " in draft.content or "1. " in draft.content
        if has_lists:
            structure_score += 1.0
            structure_feedback.append("合理使用列表")
        
        scores.structure_organization = max(1.0, min(10.0, structure_score))
        scores.dimension_feedback["structure_organization"] = "；".join(structure_feedback)
        
        # === 3. 语言表达评分 ===
        language_score = 6.0  # 基础假设语言可接受
        language_feedback = []
        
        # 句子长度分布（简单评估）
        sentences = [s for s in draft.content.replace("。", ".").replace("！", ".").replace("？", ".").split(".") if s.strip()]
        if sentences:
            avg_length = sum(len(s) for s in sentences) / len(sentences)
            if 20 < avg_length < 80:
                language_score += 1.5
                language_feedback.append("句子长度适中")
            elif avg_length > 100:
                language_score -= 0.5
                language_feedback.append("部分句子过长")
        
        # 风格符合度
        if "风格偏差" not in cot.style_consistency:
            language_score += 2.0
            language_feedback.append("风格符合要求")
        else:
            language_score -= 1.0
            language_feedback.append("风格有待调整")
        
        scores.language_expression = max(1.0, min(10.0, language_score))
        scores.dimension_feedback["language_expression"] = "；".join(language_feedback)
        
        # === 4. 格式规范评分 ===
        format_score = 6.0
        format_feedback = []
        
        # 标题使用
        if draft.title and draft.title != "未命名文档":
            format_score += 1.5
            format_feedback.append("有明确主标题")
        else:
            format_score -= 1.0
            format_feedback.append("缺少明确标题")
        
        # 格式元素
        if "**" in draft.content or "__" in draft.content:
            format_score += 0.5
            format_feedback.append("使用了强调格式")
        
        if draft.tables:
            format_score += 1.0
            format_feedback.append("包含表格")
        elif task.include_table:
            format_score -= 1.0
            format_feedback.append("缺少要求的表格")
        
        if draft.images:
            format_score += 1.0
            format_feedback.append("包含图片")
        elif task.include_image:
            format_score -= 1.0
            format_feedback.append("缺少要求的图片")
        
        scores.format_standard = max(1.0, min(10.0, format_score))
        scores.dimension_feedback["format_standard"] = "；".join(format_feedback)
        
        # === 5. 需求匹配度评分 ===
        match_score = 5.0 + cot.alignment_score * 5
        match_feedback = [f"指令对齐度 {cot.alignment_score*100:.0f}%"]
        
        if not cot.deviation_points:
            match_feedback.append("无明显偏离")
        else:
            match_feedback.append(f"存在 {len(cot.deviation_points)} 个偏离点")
        
        scores.requirement_match = max(1.0, min(10.0, match_score))
        scores.dimension_feedback["requirement_match"] = "；".join(match_feedback)
        
        return scores
    
    def _generate_comprehensive_feedback(
        self,
        draft: DocumentDraft,
        task: StructuredTask,
        cot: CoTThinking,
        scores: DimensionScore
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        生成综合反馈：优点、不足和改进建议
        """
        strengths = []
        weaknesses = []
        suggestions = []
        
        # 基于维度评分生成反馈
        if scores.content_quality >= 7:
            strengths.append(f"内容质量优秀（{scores.content_quality:.1f}分）")
        elif scores.content_quality < 5:
            weaknesses.append(f"内容质量不足（{scores.content_quality:.1f}分）")
            suggestions.append("丰富文档内容，增加更多有价值的信息")
        
        if scores.structure_organization >= 7:
            strengths.append(f"结构组织清晰（{scores.structure_organization:.1f}分）")
        elif scores.structure_organization < 5:
            weaknesses.append(f"结构组织欠佳（{scores.structure_organization:.1f}分）")
            suggestions.append("添加小标题和段落分隔，改善文档结构")
        
        if scores.language_expression >= 7:
            strengths.append(f"语言表达流畅（{scores.language_expression:.1f}分）")
        elif scores.language_expression < 5:
            weaknesses.append(f"语言表达需改进（{scores.language_expression:.1f}分）")
            suggestions.append("调整语言风格，使表达更加流畅自然")
        
        if scores.format_standard >= 7:
            strengths.append(f"格式规范良好（{scores.format_standard:.1f}分）")
        elif scores.format_standard < 5:
            weaknesses.append(f"格式规范不足（{scores.format_standard:.1f}分）")
            suggestions.append("规范文档格式，正确使用标题和列表")
        
        if scores.requirement_match >= 7:
            strengths.append(f"需求匹配度高（{scores.requirement_match:.1f}分）")
        elif scores.requirement_match < 5:
            weaknesses.append(f"需求匹配不足（{scores.requirement_match:.1f}分）")
            suggestions.append("仔细检查原始需求，确保所有要点都已覆盖")
        
        # 基于 CoT 分析添加具体反馈
        for obs in cot.key_observations:
            if obs.startswith("✓"):
                strengths.append(obs[2:].strip())
            elif obs.startswith("✗") or obs.startswith("⚠️"):
                weaknesses.append(obs[2:].strip())
        
        # 基于偏离点生成建议
        for deviation in cot.deviation_points:
            suggestions.append(f"修正：{deviation}")
        
        # 去重
        strengths = list(dict.fromkeys(strengths))
        weaknesses = list(dict.fromkeys(weaknesses))
        suggestions = list(dict.fromkeys(suggestions))
        
        return strengths, weaknesses, suggestions
    
    def _generate_overall_feedback(self, score: int, cot: CoTThinking) -> str:
        """生成总体反馈"""
        if score >= 8:
            verdict = "优秀"
            comment = "文档质量出色，满足各项要求。"
        elif score >= 7:
            verdict = "良好"
            comment = "文档质量达标，可以使用。"
        elif score >= 5:
            verdict = "一般"
            comment = "文档有改进空间，建议根据反馈修改。"
        else:
            verdict = "需改进"
            comment = "文档需要较大改进，请参考具体建议。"
        
        feedback = f"【{verdict}】评分：{score}/10。{comment}"
        feedback += f" 指令对齐度：{cot.alignment_score*100:.0f}%。"
        
        if cot.deviation_points:
            feedback += f" 发现 {len(cot.deviation_points)} 个偏离点需要处理。"
        
        return feedback
    
    def _generate_agent_feedbacks(
        self,
        draft: DocumentDraft,
        task: StructuredTask,
        cot: CoTThinking,
        scores: DimensionScore,
        strengths: List[str],
        weaknesses: List[str],
        suggestions: List[str]
    ) -> List[AgentFeedback]:
        """
        生成发送给其他 Agent 的专项反馈
        """
        feedbacks = []
        
        # === 给 WriterAgent（创作Agent）的反馈 ===
        writer_specific_points = []
        writer_action_items = []
        writer_priority = "medium"
        
        # 内容相关反馈
        if scores.content_quality < 6:
            writer_priority = "high"
            writer_specific_points.append("内容深度不够，需要扩充")
            writer_action_items.append("增加具体案例、数据或详细说明")
        
        if scores.structure_organization < 6:
            writer_specific_points.append("文档结构需要优化")
            writer_action_items.append("使用多级标题组织内容")
            writer_action_items.append("确保段落之间有逻辑过渡")
        
        if scores.language_expression < 6:
            writer_specific_points.append("语言表达需要改进")
            if task.style_requirements.get("tone") == "formal":
                writer_action_items.append("使用更专业、正式的语言")
            else:
                writer_action_items.append("使语言更加通俗易懂")
        
        # 基于偏离点生成反馈
        for deviation in cot.deviation_points:
            if "表格" in deviation:
                writer_specific_points.append("缺少必要的表格")
                writer_action_items.append("根据需求生成数据表格")
            elif "图片" in deviation:
                writer_specific_points.append("缺少必要的图片")
                writer_action_items.append("添加相关配图")
            elif "标题" in deviation:
                writer_specific_points.append("标题不符合要求")
                writer_action_items.append(f"将标题修改为：{task.title}")
        
        # 需求覆盖反馈
        uncovered = [k for k, v in cot.requirement_coverage.items() if not v]
        if uncovered:
            writer_priority = "high"
            writer_specific_points.append(f"有 {len(uncovered)} 项需求未覆盖")
            for uc in uncovered[:3]:  # 最多列出3项
                writer_action_items.append(f"补充内容：{uc}")
        
        writer_feedback_msg = "基于文档评审，创作Agent需要关注以下方面以提升文档质量。"
        if not writer_specific_points:
            writer_feedback_msg = "文档创作质量良好，继续保持当前风格和深度。"
            writer_priority = "low"
        
        feedbacks.append(AgentFeedback(
            target_agent="writer",
            priority=writer_priority,
            feedback_type="improvement" if writer_specific_points else "suggestion",
            message=writer_feedback_msg,
            specific_points=writer_specific_points,
            action_items=writer_action_items,
            context={
                "current_score": scores.calculate_weighted_score(),
                "content_score": scores.content_quality,
                "structure_score": scores.structure_organization,
                "language_score": scores.language_expression,
                "iteration": getattr(self, '_current_iteration', 1)
            }
        ))
        
        # === 给 StructurizerAgent（结构化Agent）的反馈 ===
        structurizer_specific_points = []
        structurizer_action_items = []
        structurizer_priority = "low"
        
        # 分析任务结构化的问题
        if not task.content_requirements:
            structurizer_priority = "high"
            structurizer_specific_points.append("内容要求提取不完整")
            structurizer_action_items.append("更细致地解析用户意图，提取具体的内容要求")
        
        if not task.title and cot.alignment_score < 0.7:
            structurizer_specific_points.append("标题信息缺失")
            structurizer_action_items.append("尝试从用户输入推断或询问标题")
        
        if task.include_table and not task.table_data:
            structurizer_specific_points.append("表格需求识别但数据未提取")
            structurizer_action_items.append("在识别表格需求时，尝试提取或询问具体数据")
        
        # 风格要求分析
        if not task.style_requirements:
            structurizer_specific_points.append("风格要求未明确")
            structurizer_action_items.append("识别用户对语气、长度等风格的隐含要求")
        
        # 意图相关反馈
        if "偏差" in cot.intent_alignment:
            structurizer_priority = "medium"
            structurizer_specific_points.append("意图识别可能存在偏差")
            structurizer_action_items.append("重新审视用户输入，确认真实意图")
        
        structurizer_feedback_msg = "基于文档生成结果，结构化Agent的解析可以在以下方面优化。"
        if not structurizer_specific_points:
            structurizer_feedback_msg = "任务结构化质量良好，需求解析准确完整。"
            structurizer_priority = "low"
        else:
            structurizer_priority = max(structurizer_priority, "medium")
        
        feedbacks.append(AgentFeedback(
            target_agent="structurizer",
            priority=structurizer_priority,
            feedback_type="improvement" if structurizer_specific_points else "suggestion",
            message=structurizer_feedback_msg,
            specific_points=structurizer_specific_points,
            action_items=structurizer_action_items,
            context={
                "task_completeness": len([v for v in [task.title, task.document_name, task.content_requirements] if v]) / 3,
                "requirement_coverage": cot.alignment_score,
                "original_task": task.to_dict()
            }
        ))
        
        return feedbacks
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """
        获取所有评审历史的反馈汇总
        """
        if not self.review_history:
            return {"message": "暂无评审历史"}
        
        all_writer_feedback = []
        all_structurizer_feedback = []
        score_trend = []
        
        for review in self.review_history:
            score_trend.append(review.score)
            for fb in review.agent_feedbacks:
                if fb.target_agent == "writer":
                    all_writer_feedback.append(fb.to_dict())
                elif fb.target_agent == "structurizer":
                    all_structurizer_feedback.append(fb.to_dict())
        
        return {
            "total_reviews": len(self.review_history),
            "score_trend": score_trend,
            "average_score": sum(score_trend) / len(score_trend),
            "latest_score": score_trend[-1],
            "writer_feedback_count": len(all_writer_feedback),
            "structurizer_feedback_count": len(all_structurizer_feedback),
            "latest_writer_feedback": all_writer_feedback[-1] if all_writer_feedback else None,
            "latest_structurizer_feedback": all_structurizer_feedback[-1] if all_structurizer_feedback else None
        }
    
    def _evaluate(self, draft: DocumentDraft, task: StructuredTask) -> Tuple[int, str, List[str], List[str]]:
        """评估文档（可替换为 LLM 调用）"""
        suggestions = []
        strengths = []
        score = 5  # 基础分
        
        # 检查标题
        if draft.title and draft.title != "未命名文档":
            score += 1
            strengths.append("有明确的标题")
        else:
            suggestions.append("添加一个有意义的标题")
        
        # 检查内容长度
        content_length = len(draft.content)
        if content_length > 500:
            score += 2
            strengths.append("内容充实")
        elif content_length > 200:
            score += 1
        else:
            suggestions.append("内容较短，建议扩充更多细节")
        
        # 检查是否满足任务要求
        for req in task.content_requirements:
            if req.lower() in draft.content.lower():
                score += 0.5
                strengths.append(f"覆盖了要求：{req[:20]}...")
            else:
                suggestions.append(f"未完全覆盖要求：{req[:20]}...")
        
        # 检查结构
        if "##" in draft.content or "\n\n" in draft.content:
            score += 1
            strengths.append("有良好的段落结构")
        else:
            suggestions.append("建议添加小标题或分段")
        
        # 限制分数范围
        score = max(1, min(10, int(score)))
        
        feedback = f"文档评分：{score}/10。" 
        if score >= self.pass_threshold:
            feedback += "文档质量达标，可以使用。"
        else:
            feedback += f"文档需要改进，目标分数：{self.pass_threshold}。"
        
        return score, feedback, suggestions, strengths


# ==================== 协作 Pipeline ====================

class DocumentCreationPipeline:
    """
    文档创建 Pipeline：协调三个 Agent 完成文档创建任务
    
    流程：
    1. 用户输入 → StructurizerAgent → 结构化任务
    2. 结构化任务 → WriterAgent → 文档草稿
    3. 文档草稿 → ReviewerAgent → 评审结果（含 CoT 思考和 Agent 反馈）
    4. 如果评分不达标，根据反馈返回步骤2重新创作（最多 max_iterations 轮）
    5. 生成最终反馈报告给所有 Agent
    """
    
    def __init__(
        self,
        word_tools: Dict = None,
        pass_threshold: int = 7,
        max_iterations: int = 3,
        model_config: Optional[Dict] = None,
        enable_enhanced_review: bool = True  # 是否启用增强评审
    ):
        self.structurizer = StructurizerAgent(model_config)
        self.writer = WriterAgent(word_tools, model_config)
        self.reviewer = ReviewerAgent(pass_threshold, model_config)
        self.max_iterations = max_iterations
        self.word_tools = word_tools or {}
        self.enable_enhanced_review = enable_enhanced_review
        
        # 反馈收集器
        self.feedback_history: List[Dict[str, Any]] = []
    
    def run(self, user_input: str, auto_confirm: bool = False) -> Dict[str, Any]:
        """
        运行完整的文档创建流程
        
        Args:
            user_input: 用户的自然语言输入
            auto_confirm: 是否自动确认（跳过澄清问题）
            
        Returns:
            包含最终结果的字典
        """
        result = {
            "success": False,
            "iterations": 0,
            "stages": [],
            "agent_feedbacks": []  # 新增：收集所有 Agent 反馈
        }
        
        # 阶段1：结构化
        print(f"\n{'='*60}")
        print("🔍 阶段1：结构化用户输入")
        print(f"{'='*60}")
        
        task, questions = self.structurizer.process(user_input)
        
        result["stages"].append({
            "stage": "structurize",
            "task": task.to_dict(),
            "clarification_questions": questions
        })
        
        print(f"✅ 识别意图：{task.intent}")
        print(f"📄 文档名：{task.document_name or '待确定'}")
        print(f"📌 标题：{task.title or '待确定'}")
        if task.content_requirements:
            print(f"📋 内容要求：{len(task.content_requirements)} 项")
        if task.style_requirements:
            print(f"🎨 风格要求：{task.style_requirements}")
        
        if questions and not auto_confirm:
            print(f"\n⚠️ 需要澄清的问题：")
            for q in questions:
                print(f"   - {q}")
            result["needs_clarification"] = True
            result["questions"] = questions
            return result
        
        # 阶段2-3：创作和评审循环
        iteration = 0
        draft = None
        review = None
        enhanced_review = None
        previous_enhanced_review = None
        
        while iteration < self.max_iterations:
            iteration += 1
            result["iterations"] = iteration
            
            # 阶段2：创作
            print(f"\n{'='*60}")
            print(f"✍️ 阶段2：创作文档 (第 {iteration} 轮)")
            print(f"{'='*60}")
            
            # 如果有上一轮的反馈，加入任务
            if enhanced_review and not enhanced_review.passed:
                # 使用增强版反馈
                writer_feedbacks = enhanced_review.get_feedback_for_agent("writer")
                if writer_feedbacks:
                    improvement_notes = []
                    for fb in writer_feedbacks:
                        improvement_notes.extend(fb.action_items)
                    task.additional_notes = f"改进建议：{'; '.join(improvement_notes)}"
                    print(f"📨 收到来自 Reviewer 的反馈：{len(improvement_notes)} 项改进建议")
            elif review and not review.passed:
                # 兼容基础版反馈
                task.additional_notes = f"改进建议：{'; '.join(review.improvement_suggestions)}"
            
            draft = self.writer.process(task)
            
            result["stages"].append({
                "stage": f"write_iteration_{iteration}",
                "draft": {
                    "filename": draft.filename,
                    "title": draft.title,
                    "content_preview": draft.content[:200] + "..." if len(draft.content) > 200 else draft.content
                }
            })
            
            print(f"✅ 生成文档：{draft.filename}")
            print(f"📝 内容长度：{len(draft.content)} 字符")
            
            # 阶段3：评审（增强版）
            print(f"\n{'='*60}")
            print(f"⭐ 阶段3：{'增强版' if self.enable_enhanced_review else ''}评审文档 (第 {iteration} 轮)")
            print(f"{'='*60}")
            
            if self.enable_enhanced_review:
                # 使用增强版评审
                enhanced_review = self.reviewer.process_enhanced(
                    draft, 
                    task, 
                    iteration=iteration,
                    previous_review=previous_enhanced_review
                )
                
                # 打印 CoT 思考过程
                print(f"\n  🧠 Chain of Thought 思考过程：")
                for step in enhanced_review.cot_thinking.reasoning_chain:
                    print(f"    {step}")
                
                # 打印关键观察
                if enhanced_review.cot_thinking.key_observations:
                    print(f"\n  🔍 关键观察：")
                    for obs in enhanced_review.cot_thinking.key_observations[:5]:
                        print(f"    {obs}")
                
                # 打印多维度评分
                print(f"\n  📊 多维度评分：")
                scores = enhanced_review.dimension_scores
                print(f"    • 内容质量：{scores.content_quality:.1f}/10 - {scores.dimension_feedback.get('content_quality', '')}")
                print(f"    • 结构组织：{scores.structure_organization:.1f}/10 - {scores.dimension_feedback.get('structure_organization', '')}")
                print(f"    • 语言表达：{scores.language_expression:.1f}/10 - {scores.dimension_feedback.get('language_expression', '')}")
                print(f"    • 格式规范：{scores.format_standard:.1f}/10 - {scores.dimension_feedback.get('format_standard', '')}")
                print(f"    • 需求匹配：{scores.requirement_match:.1f}/10 - {scores.dimension_feedback.get('requirement_match', '')}")
                print(f"    ────────────────────────────")
                print(f"    📈 加权总分：{scores.calculate_weighted_score():.2f}/10")
                
                # 打印总体反馈
                print(f"\n  💬 总体评价：{enhanced_review.overall_feedback}")
                
                # 打印优缺点
                if enhanced_review.strengths:
                    print(f"\n  💪 优点：")
                    for s in enhanced_review.strengths[:5]:
                        print(f"    ✓ {s}")
                
                if enhanced_review.weaknesses:
                    print(f"\n  ⚠️ 不足：")
                    for w in enhanced_review.weaknesses[:5]:
                        print(f"    ✗ {w}")
                
                if enhanced_review.improvement_suggestions:
                    print(f"\n  💡 改进建议：")
                    for s in enhanced_review.improvement_suggestions[:5]:
                        print(f"    → {s}")
                
                # 打印 Agent 反馈
                print(f"\n  📨 发送给其他 Agent 的反馈：")
                for fb in enhanced_review.agent_feedbacks:
                    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(fb.priority, "⚪")
                    print(f"\n    [{priority_icon} {fb.target_agent.upper()}] {fb.message}")
                    if fb.specific_points:
                        print(f"      要点：{', '.join(fb.specific_points[:3])}")
                    if fb.action_items:
                        print(f"      行动项：")
                        for action in fb.action_items[:3]:
                            print(f"        • {action}")
                
                # 保存反馈历史
                self.feedback_history.append({
                    "iteration": iteration,
                    "feedbacks": [fb.to_dict() for fb in enhanced_review.agent_feedbacks]
                })
                
                # 添加到结果
                result["stages"].append({
                    "stage": f"enhanced_review_iteration_{iteration}",
                    "review": enhanced_review.to_dict()
                })
                
                # 记录 Agent 反馈
                result["agent_feedbacks"].extend([fb.to_dict() for fb in enhanced_review.agent_feedbacks])
                
                print(f"\n  📊 最终评分：{enhanced_review.score}/10")
                print(f"  {'✅ 通过' if enhanced_review.passed else '❌ 需改进'}")
                
                if enhanced_review.passed:
                    break
                
                previous_enhanced_review = enhanced_review
                
            else:
                # 使用基础版评审
                review = self.reviewer.process(draft, task)
                
                result["stages"].append({
                    "stage": f"review_iteration_{iteration}",
                    "review": {
                        "score": review.score,
                        "passed": review.passed,
                        "feedback": review.feedback,
                        "suggestions": review.improvement_suggestions,
                        "strengths": review.strengths
                    }
                })
                
                print(f"📊 评分：{review.score}/10")
                print(f"{'✅ 通过' if review.passed else '❌ 需改进'}")
                
                if review.strengths:
                    print(f"💪 优点：{', '.join(review.strengths)}")
                if review.improvement_suggestions:
                    print(f"💡 建议：{', '.join(review.improvement_suggestions)}")
                
                if review.passed:
                    break
            
            if iteration < self.max_iterations:
                print(f"\n🔄 将根据反馈重新创作...")
        
        # 最终结果
        final_review = enhanced_review if self.enable_enhanced_review else review
        result["success"] = final_review.passed if final_review else False
        result["final_draft"] = {
            "filename": draft.filename,
            "title": draft.title,
            "content": draft.content,
            "tables": draft.tables,
            "images": draft.images
        } if draft else None
        
        if self.enable_enhanced_review and enhanced_review:
            result["final_review"] = enhanced_review.to_dict()
        elif review:
            result["final_review"] = {
                "score": review.score,
                "passed": review.passed,
                "feedback": review.feedback
            }
        
        # 生成最终反馈汇总
        if self.enable_enhanced_review:
            result["feedback_summary"] = self.reviewer.get_feedback_summary()
        
        print(f"\n{'='*60}")
        print(f"🏁 流程完成")
        print(f"{'='*60}")
        print(f"总轮数：{iteration}")
        print(f"最终评分：{final_review.score if final_review else 'N/A'}/10")
        print(f"状态：{'✅ 成功' if result['success'] else '❌ 未达标'}")
        
        if self.enable_enhanced_review and self.feedback_history:
            print(f"\n📋 反馈汇总：")
            summary = self.reviewer.get_feedback_summary()
            print(f"  总评审次数：{summary.get('total_reviews', 0)}")
            print(f"  平均评分：{summary.get('average_score', 0):.2f}")
            print(f"  评分趋势：{' → '.join(map(str, summary.get('score_trend', [])))}")
        
        return result
    
    def run_enhanced(self, user_input: str, auto_confirm: bool = False) -> Dict[str, Any]:
        """
        运行增强版流程（便捷方法）
        """
        self.enable_enhanced_review = True
        return self.run(user_input, auto_confirm)
    
    def get_all_agent_feedbacks(self) -> Dict[str, List[Dict]]:
        """
        获取所有 Agent 的反馈汇总
        
        Returns:
            按 Agent 分类的所有反馈
        """
        writer_feedbacks = []
        structurizer_feedbacks = []
        
        for history in self.feedback_history:
            for fb in history.get("feedbacks", []):
                if fb["target_agent"] == "writer":
                    writer_feedbacks.append({
                        "iteration": history["iteration"],
                        **fb
                    })
                elif fb["target_agent"] == "structurizer":
                    structurizer_feedbacks.append({
                        "iteration": history["iteration"],
                        **fb
                    })
        
        return {
            "writer": writer_feedbacks,
            "structurizer": structurizer_feedbacks
        }
    
    def generate_improvement_report(self) -> str:
        """
        生成改进建议报告
        
        Returns:
            格式化的改进建议报告
        """
        report_lines = [
            "=" * 60,
            "📝 Agent 改进建议报告",
            "=" * 60,
            ""
        ]
        
        all_feedbacks = self.get_all_agent_feedbacks()
        
        # Writer Agent 反馈
        writer_fbs = all_feedbacks.get("writer", [])
        if writer_fbs:
            report_lines.append("🖊️ 给创作 Agent (Writer) 的建议：")
            report_lines.append("-" * 40)
            
            # 收集所有高优先级建议
            high_priority = [fb for fb in writer_fbs if fb.get("priority") == "high"]
            if high_priority:
                report_lines.append("\n  🔴 高优先级：")
                for fb in high_priority:
                    report_lines.append(f"    • {fb.get('message', '')}")
                    for action in fb.get("action_items", [])[:3]:
                        report_lines.append(f"      → {action}")
            
            # 常见问题模式
            all_points = []
            for fb in writer_fbs:
                all_points.extend(fb.get("specific_points", []))
            
            if all_points:
                from collections import Counter
                common_issues = Counter(all_points).most_common(5)
                report_lines.append("\n  📊 常见问题：")
                for issue, count in common_issues:
                    report_lines.append(f"    • [{count}次] {issue}")
            
            report_lines.append("")
        
        # Structurizer Agent 反馈
        struct_fbs = all_feedbacks.get("structurizer", [])
        if struct_fbs:
            report_lines.append("🔍 给结构化 Agent (Structurizer) 的建议：")
            report_lines.append("-" * 40)
            
            # 收集建议
            for fb in struct_fbs:
                if fb.get("specific_points"):
                    report_lines.append(f"\n  第 {fb.get('iteration', '?')} 轮反馈：")
                    for point in fb.get("specific_points", []):
                        report_lines.append(f"    • {point}")
                    for action in fb.get("action_items", [])[:3]:
                        report_lines.append(f"      → {action}")
            
            report_lines.append("")
        
        # 总结
        summary = self.reviewer.get_feedback_summary()
        if summary.get("total_reviews", 0) > 0:
            report_lines.extend([
                "=" * 60,
                "📈 评审统计",
                "=" * 60,
                f"  • 总评审次数：{summary.get('total_reviews', 0)}",
                f"  • 平均评分：{summary.get('average_score', 0):.2f}/10",
                f"  • 最终评分：{summary.get('latest_score', 0)}/10",
                f"  • 评分趋势：{' → '.join(map(str, summary.get('score_trend', [])))}",
            ])
        
        return "\n".join(report_lines)
    
    def save_document(self, draft: DocumentDraft) -> Dict[str, Any]:
        """
        使用 Word 工具保存文档
        
        Args:
            draft: 文档草稿
            
        Returns:
            保存结果
        """
        if "create_document" in self.word_tools:
            return self.word_tools["create_document"](
                filename=draft.filename,
                title=draft.title,
                content=draft.content
            )
        return {"success": False, "error": "create_document 工具未配置"}


# ==================== AgentScope 集成（如果可用）====================

if AGENTSCOPE_AVAILABLE:
    class AgentScopeStructurizer(AgentBase):
        """AgentScope 版本的结构化 Agent"""
        
        def __init__(self, name: str = "Structurizer", model_config_name: str = None):
            super().__init__(name=name, model_config_name=model_config_name)
            self.local_agent = StructurizerAgent()
        
        def reply(self, x: Msg) -> Msg:
            task, questions = self.local_agent.process(x.content)
            return Msg(
                name=self.name,
                content=json.dumps({
                    "task": task.to_dict(),
                    "questions": questions
                }, ensure_ascii=False),
                role="assistant"
            )
    
    class AgentScopeWriter(AgentBase):
        """AgentScope 版本的创作 Agent"""
        
        def __init__(self, name: str = "Writer", model_config_name: str = None):
            super().__init__(name=name, model_config_name=model_config_name)
            self.local_agent = WriterAgent()
        
        def reply(self, x: Msg) -> Msg:
            task_data = json.loads(x.content)
            task = StructuredTask(**task_data.get("task", {}))
            draft = self.local_agent.process(task)
            return Msg(
                name=self.name,
                content=json.dumps({
                    "filename": draft.filename,
                    "title": draft.title,
                    "content": draft.content
                }, ensure_ascii=False),
                role="assistant"
            )
    
    class AgentScopeReviewer(AgentBase):
        """AgentScope 版本的评审 Agent"""
        
        def __init__(self, name: str = "Reviewer", model_config_name: str = None, pass_threshold: int = 7):
            super().__init__(name=name, model_config_name=model_config_name)
            self.local_agent = ReviewerAgent(pass_threshold)
        
        def reply(self, x: Msg) -> Msg:
            data = json.loads(x.content)
            draft = DocumentDraft(**data.get("draft", {}))
            task = StructuredTask(**data.get("task", {}))
            review = self.local_agent.process(draft, task)
            return Msg(
                name=self.name,
                content=json.dumps({
                    "score": review.score,
                    "passed": review.passed,
                    "feedback": review.feedback,
                    "suggestions": review.improvement_suggestions
                }, ensure_ascii=False),
                role="assistant"
            )


# ==================== 使用示例 ====================

def demo():
    """演示多 Agent 协作流程"""
    
    # 创建 Pipeline（启用增强评审）
    pipeline = DocumentCreationPipeline(
        pass_threshold=6,  # 降低阈值便于演示
        max_iterations=3,
        enable_enhanced_review=True  # 启用增强版评审
    )
    
    # 测试用例
    test_inputs = [
        "帮我创建一个文档叫'产品介绍'，标题是'新品发布会'，内容介绍一下我们的AI助手产品",
        "写一份年度报告，要正式一点，包含销售数据表格",
        "创建文档"  # 缺少必要信息
    ]
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n\n{'#'*60}")
        print(f"# 测试用例 {i}")
        print(f"# 用户输入：{user_input}")
        print(f"{'#'*60}")
        
        result = pipeline.run(user_input, auto_confirm=True)
        
        print(f"\n📋 结果摘要：")
        # 只打印关键信息，避免输出过长
        summary = {
            "success": result.get("success"),
            "iterations": result.get("iterations"),
            "final_score": result.get("final_review", {}).get("score") if result.get("final_review") else None
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    # 打印改进建议报告
    print("\n\n")
    print(pipeline.generate_improvement_report())


def demo_enhanced_review():
    """单独演示增强版评审功能"""
    
    print("=" * 60)
    print("🧪 增强版 ReviewerAgent 功能演示")
    print("=" * 60)
    
    # 创建测试数据
    task = StructuredTask(
        intent="create",
        document_name="test_doc.docx",
        title="AI技术白皮书",
        content_requirements=[
            "介绍人工智能的发展历史",
            "说明机器学习的基本原理",
            "探讨AI在各行业的应用"
        ],
        style_requirements={"tone": "formal", "length": "long"},
        include_table=True
    )
    
    draft = DocumentDraft(
        filename="test_doc.docx",
        title="AI技术白皮书",
        content="""# AI技术白皮书

## 引言

人工智能（AI）是计算机科学的一个重要分支，旨在创建能够执行通常需要人类智能的任务的系统。

## 发展历史

人工智能的发展可以追溯到20世纪50年代。1956年的达特茅斯会议标志着AI作为一个学科的诞生。

## 机器学习基础

机器学习是AI的核心技术之一，它使计算机能够从数据中学习，而无需显式编程。

### 主要类型
- 监督学习
- 无监督学习
- 强化学习

## 行业应用

AI已经在多个领域得到广泛应用：
- 医疗健康：疾病诊断、药物研发
- 金融服务：风险评估、欺诈检测
- 制造业：质量控制、预测性维护
""",
        tables=[],
        images=[]
    )
    
    # 创建评审 Agent
    reviewer = ReviewerAgent(pass_threshold=7)
    
    # 进行增强版评审
    print("\n🚀 开始增强版评审...\n")
    result = reviewer.process_enhanced(draft, task, iteration=1)
    
    # 打印完整结果
    print("\n" + "=" * 60)
    print("📋 评审结果详情")
    print("=" * 60)
    
    print(f"\n✨ 最终评分：{result.score}/10 ({'通过' if result.passed else '未通过'})")
    print(f"📝 总体评价：{result.overall_feedback}")
    
    print("\n🎯 CoT 思考摘要：")
    print(f"  • 任务总结：{result.cot_thinking.task_summary}")
    print(f"  • 草稿总结：{result.cot_thinking.draft_summary}")
    print(f"  • 意图对齐：{result.cot_thinking.intent_alignment}")
    print(f"  • 风格一致性：{result.cot_thinking.style_consistency}")
    print(f"  • 对齐得分：{result.cot_thinking.alignment_score * 100:.1f}%")
    
    print("\n📊 多维度评分：")
    for dim, score in [
        ("内容质量", result.dimension_scores.content_quality),
        ("结构组织", result.dimension_scores.structure_organization),
        ("语言表达", result.dimension_scores.language_expression),
        ("格式规范", result.dimension_scores.format_standard),
        ("需求匹配", result.dimension_scores.requirement_match)
    ]:
        bar = "█" * int(score) + "░" * (10 - int(score))
        print(f"  {dim}：{bar} {score:.1f}")
    
    print("\n📨 Agent 反馈：")
    for fb in result.agent_feedbacks:
        print(f"\n  [{fb.target_agent.upper()}]")
        print(f"    优先级：{fb.priority}")
        print(f"    消息：{fb.message}")
        if fb.action_items:
            print(f"    行动项：")
            for item in fb.action_items:
                print(f"      • {item}")
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "enhanced":
        demo_enhanced_review()
    else:
        demo()

