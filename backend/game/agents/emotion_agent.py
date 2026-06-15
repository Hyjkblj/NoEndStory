"""Emotion Agent — 12维情绪计算 + PAD三维映射 + 情绪衰减"""
import math
from typing import Dict, Any
from .base import BaseAgent
from .state import AgentState, EmotionState


class EmotionAgent(BaseAgent):
    """情绪Agent：计算情绪变化并更新状态"""

    # 情绪衰减率（每轮自然回落百分比）
    DECAY_RATES = {
        "stress": 0.15,
        "anxiety": 0.10,
        "emotion": 0.05,
        "happiness": 0.03,
        "sadness": 0.08,
    }

    def __init__(self):
        super().__init__("emotion")

    async def think(self, state: AgentState) -> Dict[str, Any]:
        emotion = state.emotion

        # 1. 自然衰减
        self._apply_decay(emotion)

        # 2. 基于玩家选择计算变化
        player_text = state.last_player_input.lower() if state.last_player_input else ""
        changes = self._analyze_player_impact(player_text, state)

        # 3. 应用变化
        emotion.apply_changes(changes)

        # 4. 计算 PAD 向量
        pad = emotion.pad_vector()

        return {
            "state_changes": changes,
            "current_emotion": emotion.to_dict(),
            "pad": pad,
        }

    def _apply_decay(self, emotion: EmotionState) -> None:
        for key, rate in self.DECAY_RATES.items():
            current = getattr(emotion, key)
            setattr(emotion, key, max(0.0, current * (1 - rate)))

    def _analyze_player_impact(self, text: str, state: AgentState) -> Dict[str, float]:
        """分析玩家输入对情绪的影响（基于关键词）"""
        changes = {
            "favorability": 0.0,
            "trust": 0.0,
            "happiness": 0.0,
            "emotion": 0.0,
            "stress": 0.0,
            "confidence": 0.0,
        }

        if not text:
            return changes

        # 正面关键词
        positive = {"谢谢", "喜欢你", "好的", "可以", "好", "真棒", "太好", "开心", "喜欢", "爱你", "支持", "棒"}
        # 负面关键词
        negative = {"讨厌", "不喜欢", "不行", "不好", "滚", "烦", "无聊", "恨", "生气", "失望"}
        # 支持性关键词
        supportive = {"我相信你", "你可以", "没问题", "加油", "相信", "信任"}

        for word in positive:
            if word in text:
                changes["favorability"] += 2.0
                changes["happiness"] += 1.5
        for word in negative:
            if word in text:
                changes["favorability"] -= 3.0
                changes["happiness"] -= 2.0
                changes["stress"] += 1.5
        for word in supportive:
            if word in text:
                changes["trust"] += 2.0
                changes["confidence"] += 2.0

        # Clamp 单次变化幅度
        for k in changes:
            changes[k] = max(-10.0, min(10.0, changes[k]))

        return changes
