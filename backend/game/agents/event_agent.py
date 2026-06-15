"""Event Agent — 事件池管理 + 加权采样 + 随机因子"""
import random
from typing import Dict, Any, List, Optional
from .base import BaseAgent
from .state import AgentState

# 事件模板池
EVENT_TEMPLATES = {
    "first_meeting": "角色与玩家初次相遇",
    "casual_chat": "角色与玩家闲聊日常",
    "shared_activity": "角色与玩家共同完成某件事",
    "small_conflict": "角色与玩家产生小误会",
    "personal_revelation": "角色向玩家透露个人秘密",
    "help_moment": "角色帮助玩家解决一个困难",
    "major_conflict": "角色与玩家发生严重分歧",
    "critical_choice": "角色面临关键抉择",
    "emotional_confession": "角色情感爆发表白",
    "betrayal": "角色感到被背叛",
    "reconciliation": "角色与玩家和解",
    "final_choice": "角色做出最终决定",
    "departure": "角色准备离开",
    "promise": "角色做出承诺",
}

# 混沌因子（随机事件注入概率）
CHAOS_FACTOR = 0.08


class EventAgent(BaseAgent):
    """事件Agent：根据叙事节拍选择合适事件，注入随机性"""

    def __init__(self):
        super().__init__("event")
        self._used_events: List[str] = []

    async def think(self, state: AgentState) -> Dict[str, Any]:
        beat = state.current_beat
        event_type = state.pending_event.get("type") if state.pending_event else None

        # 如果已有pending事件，使用它
        if event_type:
            event = self._build_event(event_type, state)
            state.used_event_ids.add(event_type)
            return {"event": event, "event_type": event_type}

        # 根据节拍选择事件
        if beat and beat.event_pool:
            # 加权采样：优先选择未使用的事件
            available = [e for e in beat.event_pool if e not in self._used_events]
            if not available:
                available = beat.event_pool
                self._used_events = []

            event_type = random.choice(available)

            # 混沌因子：小概率随机注入意外事件
            if random.random() < CHAOS_FACTOR:
                all_events = list(EVENT_TEMPLATES.keys())
                chaos_event = random.choice(all_events)
                if chaos_event != event_type:
                    event_type = chaos_event

            self._used_events.append(event_type)
            state.used_event_ids.add(event_type)

            event = self._build_event(event_type, state)
            return {"event": event, "event_type": event_type, "chaos": event_type not in beat.event_pool}

        return {"event": None, "event_type": None}

    def _build_event(self, event_type: str, state: AgentState) -> Dict[str, Any]:
        """构建事件对象"""
        description = EVENT_TEMPLATES.get(event_type, "角色与玩家互动")
        return {
            "type": event_type,
            "description": description,
            "scene": state.world.current_scene,
            "time": state.world.current_time,
            "weather": state.world.weather,
            "round": state.total_rounds + 1,
        }
