"""MemoryManager — 简版双层记忆"""
import json
from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """简版记忆管理器（Working + Episodic，无长期 Semantic）

    设计约束（1角色+30分钟）:
    - Working Memory: 当前对话上下文（最近10轮）
    - Episodic Memory: ChromaDB 存取的近期事件摘要
    - 不需要长期 Semantic Memory（30分钟足以装下）
    """

    def __init__(self, vector_db=None):
        self.vector_db = vector_db
        self.working_memory: List[Dict[str, Any]] = []
        self.event_summaries: List[str] = []
        self._max_working_size = 20  # 最近20条消息

    def add_to_working(self, role: str, content: str) -> None:
        self.working_memory.append({"role": role, "content": content})
        if len(self.working_memory) > self._max_working_size:
            self.working_memory = self.working_memory[-self._max_working_size:]

    def add_event(self, character_id: int, event_summary: str, metadata: Dict = None) -> None:
        self.event_summaries.append(event_summary)
        if self.vector_db:
            try:
                self.vector_db.add_event_to_collection(
                    character_id=character_id,
                    event_content=event_summary,
                    metadata=metadata or {},
                )
            except Exception as e:
                logger.warning("保存事件到向量库失败: %s", e)

    def get_recent_context(self, n: int = 10) -> List[Dict[str, Any]]:
        return self.working_memory[-n:] if self.working_memory else []

    def get_event_summaries(self, n: int = 5) -> List[str]:
        return self.event_summaries[-n:] if self.event_summaries else []

    def get_context_text(self, n: int = 8) -> str:
        """将最近N轮对话转为可注入prompt的文本"""
        recent = self.get_recent_context(n)
        lines = []
        for msg in recent:
            role_label = "角色" if msg["role"] == "character" else "玩家"
            lines.append(f"{role_label}: {msg['content']}")
        return "\n".join(lines)

    def clear(self) -> None:
        self.working_memory.clear()
        self.event_summaries.clear()
