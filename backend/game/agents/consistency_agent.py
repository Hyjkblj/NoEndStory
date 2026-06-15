"""Consistency Agent — 输出前校验"""
from typing import Dict, Any, List
from .base import BaseAgent
from .state import AgentState


class ConsistencyAgent(BaseAgent):
    """一致性守门员：在输出前校验所有生成内容"""

    # 情绪突变阈值
    MAX_EMOTION_DELTA = 30.0

    def __init__(self):
        super().__init__("consistency")

    async def think(self, state: AgentState) -> Dict[str, Any]:
        violations: List[str] = []

        # 1. 情绪突变检测
        changes = state.output_emotion_changes
        if changes:
            for key, delta in changes.items():
                if abs(delta) > self.MAX_EMOTION_DELTA:
                    violations.append(f"情绪[{key}]变化过大: {delta:.1f}")

        # 2. 对话内容校验
        dialogue = state.output_dialogue
        if dialogue:
            # 检查是否包含角色名
            if state.character_name and state.character_name not in dialogue:
                violations.append("对话缺少角色名")

            # 检查空对话
            if len(dialogue.strip()) < 5:
                violations.append("对话内容过短")

            # 检查重复性（简单检测连续相同字符）
            if self._is_repetitive(dialogue):
                violations.append("对话内容重复度过高")

        # 3. 事件连续性检测
        if len(state.event_history) >= 2:
            last = state.event_history[-1]
            event_type = state.pending_event.get("type") if state.pending_event else None
            if event_type and last.get("type") == event_type:
                violations.append(f"连续重复事件: {event_type}")

        state.consistency_checks = violations

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "severity": "error" if len(violations) >= 3 else ("warning" if violations else "ok"),
        }

    def _is_repetitive(self, text: str, threshold: float = 0.6) -> bool:
        """检测文本是否重复度过高（简单字符级）"""
        if len(text) < 10:
            return False
        unique = len(set(text))
        return unique / len(text) < 0.3
