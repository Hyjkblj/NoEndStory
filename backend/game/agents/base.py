"""Agent 抽象基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from utils.logger import get_logger


class BaseAgent(ABC):
    """所有 Agent 的抽象基类

    每个 Agent 实现 think() → action 模式：
    - think(state): 分析当前状态，做出决策
    - observe(observation): 接收外部反馈，更新内部状态

    Brain-Memory-Tools 三层架构：
    - Brain (think): 核心决策逻辑
    - Memory (state): 状态持久化
    - Tools (_call_llm, _query_db): 外部能力
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"agent.{name}")

    @abstractmethod
    async def think(self, state: "AgentState") -> Dict[str, Any]:
        """核心决策：分析状态 → 返回行动

        Args:
            state: 当前全局 AgentState

        Returns:
            action dict，包含决策结果
        """
        ...

    def observe(self, observation: Dict[str, Any]) -> None:
        """接收外部反馈（可选实现）"""
        pass

    def reset(self) -> None:
        """重置 Agent 内部状态（可选实现）"""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.name})>"
