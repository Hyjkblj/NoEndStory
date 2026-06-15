"""Director Agent — 剧情走向 + 节奏控制 + 结局判断"""
import random
from typing import Dict, Any, List, Optional
from .base import BaseAgent
from .state import AgentState, SessionPhase, NarrativeBeat
from .narrative_beats import get_current_beat


class DirectorAgent(BaseAgent):
    """导演Agent：内含 NarrativePlanner + EventSelector + FutureEvaluator"""

    def __init__(self, text_gen=None, db_manager=None):
        super().__init__("director")
        self.text_gen = text_gen
        self.db_manager = db_manager

    async def think(self, state: AgentState) -> Dict[str, Any]:
        """导演决策流程"""
        # 1. 判断当前叙事节拍
        beat = self._plan_beat(state)
        state.current_beat = beat
        state.phase = beat.phase if beat else state.phase

        # 2. 检查是否结束
        if self._should_end(state):
            state.phase = SessionPhase.ENDING
            return {"action": "end_game", "reason": "game_time_exceeded"}

        # 3. 选择事件类型
        event = self._select_event(beat, state)

        return {
            "action": "continue",
            "beat": beat,
            "selected_event": event,
            "phase": state.phase.value,
        }

    def _plan_beat(self, state: AgentState) -> Optional[NarrativeBeat]:
        """根据已过时间返回当前叙事节拍"""
        elapsed = state.world.elapsed_minutes
        return get_current_beat(elapsed)

    def _should_end(self, state: AgentState) -> bool:
        """判断游戏是否应该结束"""
        elapsed = state.world.elapsed_minutes
        if elapsed >= 30.0:
            return True
        if state.total_rounds >= 25:
            return True
        return False

    def _select_event(self, beat: Optional[NarrativeBeat], state: AgentState) -> Optional[str]:
        """加权采样选择事件类型"""
        if not beat or not beat.event_pool:
            return None
        available = [e for e in beat.event_pool if e not in state.used_event_ids]
        if not available:
            available = beat.event_pool
        return random.choice(available) if available else None

    def evaluate_candidates(self, candidates: List[Dict], state: AgentState) -> Dict:
        """3候选评分（简化版 FutureEvaluator，非MCTS）

        评分维度：
        1. 情绪影响分（是否符合当前阶段的情绪基调）
        2. 一致性分（是否与已有事件冲突）
        3. 叙事节拍匹配分
        """
        if not candidates:
            return {}

        beat = state.current_beat
        scored = []
        for c in candidates:
            score = 0.0
            # 情绪影响分
            emotion_changes = c.get("state_changes", {})
            if beat and beat.emotion_target == "intense":
                score += abs(sum(emotion_changes.values())) * 0.5
            elif beat and beat.emotion_target == "resolution":
                happiness_delta = emotion_changes.get("happiness", 0)
                score += happiness_delta * 0.5

            # 新颖性分（避免重复事件）
            event_id = c.get("id", "")
            if event_id not in state.used_event_ids:
                score += 1.0

            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else candidates[-1]
