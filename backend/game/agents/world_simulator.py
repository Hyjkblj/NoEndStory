"""World Simulator — 游戏内时间推进 + 场景切换"""
import random
from typing import Dict, Any
from .base import BaseAgent
from .state import AgentState

# 每个阶段默认推进时间（分钟）
PHASE_TIME_INCREMENT = {
    "opening": 1.5,
    "rising": 2.0,
    "climax": 2.5,
    "resolution": 2.0,
}

# 场景切换概率（每轮）
SCENE_CHANGE_PROBABILITY = 0.15

# 天气循环
WEATHER_CYCLE = ["clear", "clear", "clear", "cloudy", "cloudy", "rain", "clear"]


class WorldSimulator(BaseAgent):
    """世界模拟器：推进游戏时间、管理天气、触发场景切换"""

    def __init__(self, scenes_data=None):
        super().__init__("world_simulator")
        self.scenes_data = scenes_data or {}
        self._weather_index = 0

    async def think(self, state: AgentState) -> Dict[str, Any]:
        world = state.world

        # 1. 推进时间
        phase = state.phase.value if state.phase else "rising"
        increment = PHASE_TIME_INCREMENT.get(phase, 2.0)
        world.elapsed_minutes += increment + random.uniform(-0.3, 0.3)

        # 2. 更新时间段
        world.time_of_day_progress = world.elapsed_minutes / 30.0
        if world.time_of_day_progress < 0.3:
            world.current_time = "morning"
        elif world.time_of_day_progress < 0.7:
            world.current_time = "afternoon"
        else:
            world.current_time = "evening"

        # 3. 天气变化（每3轮变一次）
        if state.total_rounds % 3 == 0:
            self._weather_index = (self._weather_index + 1) % len(WEATHER_CYCLE)
            world.weather = WEATHER_CYCLE[self._weather_index]

        # 4. 场景切换
        scene_changed = False
        if random.random() < SCENE_CHANGE_PROBABILITY and self.scenes_data:
            available = [s for s in self.scenes_data if s != world.current_scene]
            if available:
                world.current_scene = random.choice(available)
                scene_changed = True

        return {
            "elapsed_minutes": round(world.elapsed_minutes, 1),
            "current_time": world.current_time,
            "weather": world.weather,
            "scene": world.current_scene,
            "scene_changed": scene_changed,
            "time_of_day_progress": round(world.time_of_day_progress, 3),
        }
