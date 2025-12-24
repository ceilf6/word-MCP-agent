"""
记忆系统模块

提供三层记忆架构：
1. 短期记忆 (Short-term Memory) - 当前会话的对话历史
2. 工作记忆 (Working Memory) - 当前任务的上下文信息
3. 长期记忆 (Long-term Memory) - 持久化的重要信息

使用方式：
    from memory import MemoryManager
    
    memory = MemoryManager()
    session = memory.get_or_create_session("user_123")
    session.add_message("user", "创建一个文档")
    session.add_message("assistant", "好的，我来帮您创建")
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import deque
import threading
import logging

logger = logging.getLogger(__name__)

# 记忆存储目录
MEMORY_DIR = Path(__file__).parent / "memory_store"
MEMORY_DIR.mkdir(exist_ok=True)


@dataclass
class Message:
    """单条消息"""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    def to_llm_format(self) -> dict:
        """转换为 LLM API 格式"""
        return {
            "role": self.role,
            "content": self.content
        }


@dataclass
class MemoryItem:
    """长期记忆项"""
    id: str
    content: str
    category: str  # "fact", "preference", "context", "summary"
    importance: float  # 0-1，重要程度
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


class ShortTermMemory:
    """
    短期记忆 - 当前会话的对话历史
    
    特点：
    - 有限容量（默认保留最近 20 轮对话）
    - 自动滑动窗口
    - 会话结束后可选择性保存到长期记忆
    """
    
    def __init__(self, max_messages: int = 40):  # 20轮对话 = 40条消息
        self.max_messages = max_messages
        self.messages: deque = deque(maxlen=max_messages)
        self.system_prompt: Optional[str] = None
    
    def set_system_prompt(self, prompt: str):
        """设置系统提示词"""
        self.system_prompt = prompt
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """添加消息"""
        msg = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(msg)
        logger.debug(f"[短期记忆] 添加消息: {role} - {content[:50]}...")
    
    def get_messages(self, include_system: bool = True) -> List[Message]:
        """获取所有消息"""
        messages = list(self.messages)
        if include_system and self.system_prompt:
            system_msg = Message(role="system", content=self.system_prompt)
            return [system_msg] + messages
        return messages
    
    def get_llm_messages(self, include_system: bool = True) -> List[dict]:
        """获取 LLM 格式的消息列表"""
        return [msg.to_llm_format() for msg in self.get_messages(include_system)]
    
    def get_recent(self, n: int = 10) -> List[Message]:
        """获取最近 n 条消息"""
        messages = list(self.messages)
        return messages[-n:] if len(messages) > n else messages
    
    def clear(self):
        """清空消息"""
        self.messages.clear()
    
    def __len__(self) -> int:
        return len(self.messages)


class WorkingMemory:
    """
    工作记忆 - 当前任务的上下文信息
    
    用于存储当前任务相关的临时信息，如：
    - 当前操作的文档名
    - 用户提取的参数
    - 中间步骤的结果
    """
    
    def __init__(self):
        self.context: Dict[str, Any] = {}
        self.task_stack: List[Dict] = []  # 任务栈，支持嵌套任务
    
    def set(self, key: str, value: Any):
        """设置上下文变量"""
        self.context[key] = value
        logger.debug(f"[工作记忆] 设置: {key} = {str(value)[:50]}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文变量"""
        return self.context.get(key, default)
    
    def remove(self, key: str):
        """移除上下文变量"""
        self.context.pop(key, None)
    
    def push_task(self, task_name: str, params: Dict = None):
        """推入新任务"""
        self.task_stack.append({
            "name": task_name,
            "params": params or {},
            "started_at": datetime.now().isoformat()
        })
        logger.debug(f"[工作记忆] 推入任务: {task_name}")
    
    def pop_task(self) -> Optional[Dict]:
        """弹出任务"""
        if self.task_stack:
            return self.task_stack.pop()
        return None
    
    def current_task(self) -> Optional[Dict]:
        """获取当前任务"""
        return self.task_stack[-1] if self.task_stack else None
    
    def clear(self):
        """清空工作记忆"""
        self.context.clear()
        self.task_stack.clear()
    
    def get_summary(self) -> str:
        """获取工作记忆摘要"""
        summary_parts = []
        
        if self.context:
            summary_parts.append("当前上下文:")
            for k, v in self.context.items():
                summary_parts.append(f"  - {k}: {str(v)[:100]}")
        
        if self.task_stack:
            summary_parts.append(f"当前任务栈 ({len(self.task_stack)} 个任务):")
            for task in self.task_stack:
                summary_parts.append(f"  - {task['name']}")
        
        return "\n".join(summary_parts) if summary_parts else "工作记忆为空"


class LongTermMemory:
    """
    长期记忆 - 持久化的重要信息
    
    特点：
    - 持久化存储到 JSON 文件
    - 按重要性和访问频率排序
    - 支持分类和标签
    - 自动清理不重要的旧记忆
    """
    
    def __init__(self, session_id: str, max_items: int = 100):
        self.session_id = session_id
        self.max_items = max_items
        self.file_path = MEMORY_DIR / f"{session_id}_long_term.json"
        self.items: Dict[str, MemoryItem] = {}
        self._load()
    
    def _generate_id(self, content: str) -> str:
        """生成记忆项 ID"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _load(self):
        """从文件加载记忆"""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item_data in data.get("items", []):
                        item = MemoryItem(**item_data)
                        self.items[item.id] = item
                logger.info(f"[长期记忆] 加载了 {len(self.items)} 条记忆")
            except Exception as e:
                logger.error(f"[长期记忆] 加载失败: {e}")
    
    def _save(self):
        """保存记忆到文件"""
        try:
            data = {
                "session_id": self.session_id,
                "updated_at": datetime.now().isoformat(),
                "items": [item.to_dict() for item in self.items.values()]
            }
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"[长期记忆] 保存了 {len(self.items)} 条记忆")
        except Exception as e:
            logger.error(f"[长期记忆] 保存失败: {e}")
    
    def add(self, content: str, category: str = "fact", importance: float = 0.5, tags: List[str] = None) -> str:
        """添加记忆"""
        item_id = self._generate_id(content)
        
        if item_id in self.items:
            # 更新已存在的记忆
            self.items[item_id].access_count += 1
            self.items[item_id].last_accessed = datetime.now().isoformat()
            self.items[item_id].importance = max(self.items[item_id].importance, importance)
        else:
            # 添加新记忆
            item = MemoryItem(
                id=item_id,
                content=content,
                category=category,
                importance=importance,
                tags=tags or []
            )
            self.items[item_id] = item
            logger.info(f"[长期记忆] 添加: {content[:50]}... (重要性: {importance})")
        
        # 如果超过最大容量，清理旧记忆
        if len(self.items) > self.max_items:
            self._cleanup()
        
        self._save()
        return item_id
    
    def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        if item_id in self.items:
            self.items[item_id].access_count += 1
            self.items[item_id].last_accessed = datetime.now().isoformat()
            return self.items[item_id]
        return None
    
    def search(self, query: str, category: str = None, limit: int = 5) -> List[MemoryItem]:
        """搜索相关记忆（简单关键词匹配）"""
        results = []
        query_lower = query.lower()
        
        for item in self.items.values():
            if category and item.category != category:
                continue
            
            # 简单的关键词匹配评分
            score = 0
            if query_lower in item.content.lower():
                score += 1
            for tag in item.tags:
                if query_lower in tag.lower():
                    score += 0.5
            
            if score > 0:
                results.append((item, score + item.importance))
        
        # 按评分排序
        results.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in results[:limit]]
    
    def get_by_category(self, category: str) -> List[MemoryItem]:
        """按分类获取记忆"""
        return [item for item in self.items.values() if item.category == category]
    
    def get_important(self, threshold: float = 0.7) -> List[MemoryItem]:
        """获取重要记忆"""
        return [item for item in self.items.values() if item.importance >= threshold]
    
    def remove(self, item_id: str) -> bool:
        """删除记忆"""
        if item_id in self.items:
            del self.items[item_id]
            self._save()
            return True
        return False
    
    def _cleanup(self):
        """清理不重要的旧记忆"""
        # 按重要性和访问次数排序
        sorted_items = sorted(
            self.items.values(),
            key=lambda x: (x.importance, x.access_count),
            reverse=True
        )
        
        # 保留前 max_items 个
        keep_ids = {item.id for item in sorted_items[:self.max_items]}
        removed = [k for k in self.items.keys() if k not in keep_ids]
        
        for item_id in removed:
            del self.items[item_id]
        
        if removed:
            logger.info(f"[长期记忆] 清理了 {len(removed)} 条旧记忆")
    
    def clear(self):
        """清空所有记忆"""
        self.items.clear()
        self._save()
    
    def get_summary(self) -> str:
        """获取长期记忆摘要"""
        if not self.items:
            return "长期记忆为空"
        
        categories = {}
        for item in self.items.values():
            categories[item.category] = categories.get(item.category, 0) + 1
        
        summary = f"长期记忆共 {len(self.items)} 条:\n"
        for cat, count in categories.items():
            summary += f"  - {cat}: {count} 条\n"
        
        # 列出重要记忆
        important = self.get_important(0.7)
        if important:
            summary += "\n重要记忆:\n"
            for item in important[:5]:
                summary += f"  • {item.content[:60]}...\n"
        
        return summary


class Session:
    """
    会话类 - 管理单个用户会话的所有记忆
    """
    
    def __init__(self, session_id: str, system_prompt: str = None):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        
        # 三层记忆
        self.short_term = ShortTermMemory()
        self.working = WorkingMemory()
        self.long_term = LongTermMemory(session_id)
        
        if system_prompt:
            self.short_term.set_system_prompt(system_prompt)
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """添加消息到短期记忆"""
        self.short_term.add_message(role, content, metadata)
        self.last_active = datetime.now()
        
        # 自动提取重要信息到长期记忆
        self._extract_to_long_term(role, content)
    
    def _extract_to_long_term(self, role: str, content: str):
        """自动从对话中提取重要信息"""
        # 用户偏好
        if role == "user":
            # 检测文件名偏好
            if "叫" in content or "命名" in content or "文件名" in content:
                self.long_term.add(
                    f"用户提到的文件命名偏好: {content[:100]}",
                    category="preference",
                    importance=0.6,
                    tags=["文件名", "偏好"]
                )
            
            # 检测风格偏好
            if any(kw in content for kw in ["正式", "轻松", "专业", "简洁", "详细"]):
                self.long_term.add(
                    f"用户的写作风格偏好: {content[:100]}",
                    category="preference",
                    importance=0.7,
                    tags=["风格", "偏好"]
                )
        
        # 助手执行的操作
        if role == "assistant":
            if "创建" in content and "成功" in content:
                self.long_term.add(
                    f"成功创建文档: {content[:100]}",
                    category="fact",
                    importance=0.5,
                    tags=["文档", "创建"]
                )
    
    def get_context_for_llm(self) -> List[dict]:
        """获取完整的 LLM 上下文（包含记忆摘要）"""
        messages = []
        
        # 系统提示词
        if self.short_term.system_prompt:
            messages.append({
                "role": "system",
                "content": self.short_term.system_prompt
            })
        
        # 长期记忆摘要（如果有重要记忆）
        important_memories = self.long_term.get_important(0.6)
        if important_memories:
            memory_context = "【历史记忆】\n"
            for item in important_memories[:5]:
                memory_context += f"- {item.content}\n"
            messages.append({
                "role": "system",
                "content": memory_context
            })
        
        # 工作记忆（如果有当前任务）
        if self.working.context or self.working.task_stack:
            messages.append({
                "role": "system",
                "content": f"【当前工作状态】\n{self.working.get_summary()}"
            })
        
        # 短期记忆（对话历史）
        for msg in self.short_term.get_messages(include_system=False):
            messages.append(msg.to_llm_format())
        
        return messages
    
    def remember(self, content: str, category: str = "fact", importance: float = 0.5, tags: List[str] = None):
        """主动添加到长期记忆"""
        return self.long_term.add(content, category, importance, tags)
    
    def recall(self, query: str, limit: int = 5) -> List[MemoryItem]:
        """从长期记忆中检索"""
        return self.long_term.search(query, limit=limit)
    
    def get_stats(self) -> dict:
        """获取会话统计"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "short_term_messages": len(self.short_term),
            "working_memory_items": len(self.working.context),
            "long_term_memories": len(self.long_term.items)
        }


class MemoryManager:
    """
    记忆管理器 - 管理所有会话的记忆
    
    单例模式，全局唯一
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.sessions: Dict[str, Session] = {}
        self.default_system_prompt: Optional[str] = None
        self._initialized = True
        logger.info("[记忆管理器] 初始化完成")
    
    def set_default_system_prompt(self, prompt: str):
        """设置默认系统提示词"""
        self.default_system_prompt = prompt
    
    def get_or_create_session(self, session_id: str, system_prompt: str = None) -> Session:
        """获取或创建会话"""
        if session_id not in self.sessions:
            prompt = system_prompt or self.default_system_prompt
            self.sessions[session_id] = Session(session_id, prompt)
            logger.info(f"[记忆管理器] 创建新会话: {session_id}")
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话（不创建）"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"[记忆管理器] 删除会话: {session_id}")
            return True
        return False
    
    def list_sessions(self) -> List[dict]:
        """列出所有会话"""
        return [session.get_stats() for session in self.sessions.values()]
    
    def cleanup_inactive(self, hours: int = 24):
        """清理不活跃的会话"""
        threshold = datetime.now() - timedelta(hours=hours)
        to_delete = [
            sid for sid, session in self.sessions.items()
            if session.last_active < threshold
        ]
        
        for sid in to_delete:
            self.delete_session(sid)
        
        if to_delete:
            logger.info(f"[记忆管理器] 清理了 {len(to_delete)} 个不活跃会话")


# 全局记忆管理器实例
memory_manager = MemoryManager()


# ==================== 便捷函数 ====================

def get_session(session_id: str = "default") -> Session:
    """获取或创建会话"""
    return memory_manager.get_or_create_session(session_id)


def remember(content: str, session_id: str = "default", **kwargs) -> str:
    """添加到长期记忆"""
    session = get_session(session_id)
    return session.remember(content, **kwargs)


def recall(query: str, session_id: str = "default", limit: int = 5) -> List[MemoryItem]:
    """从长期记忆检索"""
    session = get_session(session_id)
    return session.recall(query, limit)

