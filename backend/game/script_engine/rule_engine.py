"""规则引擎：负责所有计算和决策

职责：
- 情绪计算（纯规则，不依赖 AI）
- 事件结束判定
- 结局触发判定
- 选项 state_changes 生成
"""
import random
from typing import Optional
from .models import EmotionState, KeyBeat, EventDraft, PlayerOption
from .pad_space import compute_pad_vector, classify_mood, compute_intensity


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


# 叙事阶段修正系数
STAGE_MULTIPLIER = {
    'opening': 0.6,
    'rising': 1.0,
    'climax': 1.5,
    'resolution': 0.8,
}


class RuleEngine:
    """规则引擎"""

    def calculate_emotion_change(
        self,
        current: EmotionState,
        option_state_changes: dict,
        narrative_beat: str,
        beat_emotion_target: Optional[dict] = None,
    ) -> EmotionState:
        """计算情绪变化（纯规则）"""
        multiplier = STAGE_MULTIPLIER.get(narrative_beat, 1.0)
        new_emotion = current.copy()

        # 应用选项的 state_changes
        for dim, delta in option_state_changes.items():
            if hasattr(new_emotion, dim):
                current_val = getattr(new_emotion, dim)
                new_val = current_val + delta * multiplier
                setattr(new_emotion, dim, clamp(new_val, 0, 100))

        # 情绪衰减
        new_emotion = self._apply_decay(new_emotion)

        # 节拍目标软约束
        if beat_emotion_target:
            new_emotion = self._apply_beat_soft_constraint(new_emotion, beat_emotion_target)

        return new_emotion

    def _apply_decay(self, emotion: EmotionState) -> EmotionState:
        """情绪衰减：极端值向中间回归"""
        decay_rate = 0.02
        new = emotion.copy()

        for dim in ['stress', 'anxiety', 'hostility']:
            val = getattr(new, dim)
            if val > 50:
                setattr(new, dim, val - (val - 50) * decay_rate)

        for dim in ['happiness', 'sadness']:
            val = getattr(new, dim)
            if abs(val - 50) > 20:
                setattr(new, dim, val + (50 - val) * decay_rate)

        return new

    def _apply_beat_soft_constraint(
        self,
        emotion: EmotionState,
        target_range: dict,
    ) -> EmotionState:
        """节拍目标软约束"""
        correction = 0.1
        new = emotion.copy()

        for dim, (low, high) in target_range.items():
            if hasattr(new, dim):
                val = getattr(new, dim)
                if val < low:
                    setattr(new, dim, val + (low - val) * correction)
                elif val > high:
                    setattr(new, dim, val - (val - high) * correction)

        return new

    def should_advance_event(
        self,
        current_round: int,
        event: EventDraft,
        emotion: EmotionState,
    ) -> tuple[bool, str]:
        """判定当前事件是否应该结束"""
        estimated = event.estimated_rounds

        # 最少轮次保护
        if current_round < estimated - 1:
            return False, "未达到最少轮次"

        # 最多轮次硬上限
        if current_round >= estimated + 2:
            return True, "达到最多轮次"

        # 达到预估轮次后渐进式结束
        if current_round >= estimated:
            excess = current_round - estimated
            prob = min(0.6, excess * 0.2)
            if random.random() < prob:
                return True, "渐进式结束"

        return False, "继续"

    def should_trigger_ending(
        self,
        total_rounds: int,
        total_events: int,
        emotion: EmotionState,
        narrative_beat: str,
        anchor_progress: float = 0.0,
    ) -> tuple[bool, str, Optional[str]]:
        """判定是否触发结局

        Returns:
            (是否触发, 触发原因, 结局类型)
        """
        # 硬上限
        if total_rounds >= 25:
            return True, "轮次硬上限", self._classify_ending(emotion)

        if total_events >= 7:
            return True, "事件硬上限", self._classify_ending(emotion)

        # 情绪极化触发
        if total_rounds >= 8:
            if emotion.favorability >= 85 and emotion.trust >= 75 and emotion.happiness >= 70:
                return True, "情绪极化-美好", "happy_ending"

            if emotion.hostility >= 70:
                return True, "情绪极化-敌意", "bad_ending"

            if emotion.favorability <= 15 and emotion.trust <= 20:
                return True, "情绪极化-崩塌", "bad_ending"

        # 锚点完成度 + 轮次
        if total_rounds >= 12 and anchor_progress >= 0.75:
            return True, "锚点基本完成", self._classify_ending(emotion)

        # 收束阶段 + 情绪稳定
        if narrative_beat == 'resolution' and total_rounds >= 15:
            pad = compute_pad_vector(emotion)
            intensity = compute_intensity(*pad)
            if intensity < 0.4:
                return True, "收束阶段情绪稳定", self._classify_ending(emotion)

        # 渐进式结束
        if total_rounds >= 15:
            prob = min(0.5, (total_rounds - 15) * 0.05)
            if random.random() < prob:
                return True, "渐进式结束", self._classify_ending(emotion)

        return False, "继续", None

    def _classify_ending(self, emotion: EmotionState) -> str:
        """根据情绪状态分类结局"""
        pad = compute_pad_vector(emotion)
        p, a, d = pad
        intensity = compute_intensity(p, a, d)

        if p >= 0.3 and d >= 0.2:
            return "happy_ending"

        if p <= -0.3 and a >= 0.2:
            return "bad_ending"

        if p <= -0.2 and a <= 0 and d <= 0:
            return "bittersweet_ending"

        return "open_ending"

    def generate_option_state_changes(
        self,
        directions: list[str],
        current_emotion: EmotionState,
    ) -> list[dict]:
        """为选项方向生成 state_changes"""
        presets = []
        for direction in directions:
            if any(k in direction for k in ['积极', '关心', '温柔', '支持', '主动']):
                presets.append({
                    'favorability': random.randint(5, 12),
                    'trust': random.randint(3, 8),
                    'happiness': random.randint(3, 8),
                    'anxiety': random.randint(-5, -2),
                })
            elif any(k in direction for k in ['消极', '冷漠', '拒绝', '回避', '离开']):
                presets.append({
                    'favorability': random.randint(-8, -3),
                    'trust': random.randint(-5, -2),
                    'hostility': random.randint(2, 6),
                    'sadness': random.randint(2, 5),
                })
            else:
                presets.append({
                    'favorability': random.randint(-2, 5),
                    'trust': random.randint(-1, 3),
                    'caution': random.randint(0, 3),
                })
        return presets
