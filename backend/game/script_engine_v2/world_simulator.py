"""WorldSimulator — 纯规则执行器

职责：
  - 时间推进（按阶段步长）
  - 天气变化（循环队列）
  - 情绪变化应用（加法）
  - 情绪衰减
  - PAD 向量计算

不负责：
  - 场景切换（由 ScriptEngine 决定）
  - 事件选择（由 ScriptEngine 决定）
  - 任何 LLM 调用
"""
import random
from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger("world_simulator")


class WorldSimulator:
    """世界模拟器 — 纯规则执行器"""

    PHASE_TIME_INCREMENT = {
        "opening": 1.5,
        "rising": 2.0,
        "climax": 2.5,
        "resolution": 2.0,
        "ending": 1.0,
    }

    WEATHER_CYCLE = ["clear", "clear", "clear", "cloudy", "cloudy", "rain", "clear"]

    DECAY_RATES = {
        "stress": 0.15,
        "anxiety": 0.10,
        "emotion": 0.05,
        "happiness": 0.03,
        "sadness": 0.08,
    }

    def __init__(self):
        self._weather_index = 0

    def advance_time(self, world, phase: str) -> None:
        """推进时间

        Args:
            world: WorldState 对象
            phase: 当前叙事阶段
        """
        increment = self.PHASE_TIME_INCREMENT.get(phase, 2.0)
        world.elapsed_minutes += increment + random.uniform(-0.3, 0.3)
        world.time_of_day_progress = world.elapsed_minutes / 30.0

        if world.time_of_day_progress < 0.3:
            world.current_time = "morning"
        elif world.time_of_day_progress < 0.7:
            world.current_time = "afternoon"
        else:
            world.current_time = "evening"

    def update_weather(self, round_num: int, world) -> None:
        """更新天气

        Args:
            round_num: 当前轮次
            world: WorldState 对象
        """
        if round_num % 3 == 0:
            self._weather_index = (self._weather_index + 1) % len(self.WEATHER_CYCLE)
            world.weather = self.WEATHER_CYCLE[self._weather_index]

    def apply_emotion_changes(self, emotion, changes: Dict[str, float]) -> None:
        """应用情绪变化

        Args:
            emotion: EmotionState 对象
            changes: 变化量字典
        """
        for key, delta in changes.items():
            if hasattr(emotion, key):
                current = getattr(emotion, key)
                setattr(emotion, key, max(0.0, min(100.0, current + delta)))

    def apply_decay(self, emotion) -> None:
        """情绪衰减

        Args:
            emotion: EmotionState 对象
        """
        for key, rate in self.DECAY_RATES.items():
            if hasattr(emotion, key):
                current = getattr(emotion, key)
                setattr(emotion, key, max(0.0, current * (1 - rate)))

    def calculate_pad(self, emotion) -> Dict[str, Any]:
        """计算 PAD 向量

        Args:
            emotion: EmotionState 对象

        Returns:
            {"pleasure": float, "arousal": float, "dominance": float, "mood": str}
        """
        try:
            from services.tts_emotion_engine import compute_pad_from_emotion, classify_mood
            p, a, d = compute_pad_from_emotion(emotion)
            mood = classify_mood(p, a, d)
            return {"pleasure": p, "arousal": a, "dominance": d, "mood": mood}
        except ImportError:
            # 降级：简化计算
            p = (emotion.happiness - emotion.sadness + emotion.favorability / 2) / 2 / 100
            a = (emotion.emotion + emotion.stress + emotion.anxiety) / 3 / 100
            d = (emotion.confidence + emotion.initiative - emotion.caution) / 2 / 100
            return {"pleasure": p, "arousal": a, "dominance": d, "mood": "neutral"}
