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
    
    def process(self, draft: DocumentDraft, task: StructuredTask) -> ReviewResult:
        """
        评审文档草稿
        
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
    3. 文档草稿 → ReviewerAgent → 评审结果
    4. 如果评分不达标，返回步骤2重新创作（最多 max_iterations 轮）
    """
    
    def __init__(
        self,
        word_tools: Dict = None,
        pass_threshold: int = 7,
        max_iterations: int = 3,
        model_config: Optional[Dict] = None
    ):
        self.structurizer = StructurizerAgent(model_config)
        self.writer = WriterAgent(word_tools, model_config)
        self.reviewer = ReviewerAgent(pass_threshold, model_config)
        self.max_iterations = max_iterations
        self.word_tools = word_tools or {}
    
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
            "stages": []
        }
        
        # 阶段1：结构化
        print(f"\n{'='*50}")
        print("🔍 阶段1：结构化用户输入")
        print(f"{'='*50}")
        
        task, questions = self.structurizer.process(user_input)
        
        result["stages"].append({
            "stage": "structurize",
            "task": task.to_dict(),
            "clarification_questions": questions
        })
        
        print(f"✅ 识别意图：{task.intent}")
        print(f"📄 文档名：{task.document_name or '待确定'}")
        print(f"📌 标题：{task.title or '待确定'}")
        
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
        
        while iteration < self.max_iterations:
            iteration += 1
            result["iterations"] = iteration
            
            # 阶段2：创作
            print(f"\n{'='*50}")
            print(f"✍️ 阶段2：创作文档 (第 {iteration} 轮)")
            print(f"{'='*50}")
            
            # 如果有上一轮的反馈，加入任务
            if review and not review.passed:
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
            
            # 阶段3：评审
            print(f"\n{'='*50}")
            print(f"⭐ 阶段3：评审文档 (第 {iteration} 轮)")
            print(f"{'='*50}")
            
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
        result["success"] = review.passed if review else False
        result["final_draft"] = {
            "filename": draft.filename,
            "title": draft.title,
            "content": draft.content,
            "tables": draft.tables,
            "images": draft.images
        } if draft else None
        result["final_review"] = {
            "score": review.score,
            "passed": review.passed,
            "feedback": review.feedback
        } if review else None
        
        print(f"\n{'='*50}")
        print(f"🏁 流程完成")
        print(f"{'='*50}")
        print(f"总轮数：{iteration}")
        print(f"最终评分：{review.score if review else 'N/A'}/10")
        print(f"状态：{'✅ 成功' if result['success'] else '❌ 未达标'}")
        
        return result
    
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
    
    # 创建 Pipeline
    pipeline = DocumentCreationPipeline(
        pass_threshold=6,  # 降低阈值便于演示
        max_iterations=3
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
        print(json.dumps(result, indent=2, ensure_ascii=False)[:1000])


if __name__ == "__main__":
    demo()

