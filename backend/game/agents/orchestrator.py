"""AgentOrchestrator — 简单顺序状态机，串联所有 Agent"""
import threading
import time
from typing import Dict, Any, Optional
from .base import BaseAgent
from .state import AgentState, SessionPhase, WorldState, EmotionState
from .director_agent import DirectorAgent
from .emotion_agent import EmotionAgent
from .world_simulator import WorldSimulator
from .event_agent import EventAgent
from .consistency_agent import ConsistencyAgent
from .dialogue_agent import DialogueAgent
from .memory import MemoryManager
from utils.logger import get_logger

logger = get_logger("orchestrator")


class AgentOrchestrator:
    """Agent 编排器：顺序状态机

    数据流：
    User Input → Director → Emotion/World/Event → Consistency → Dialogue → Output
                  │              │                    │
                  └── 决策方向    └── 状态更新          └── 校验门

    支持多会话并发：每个 thread_id 拥有独立的 AgentState。
    """

    def __init__(
        self,
        text_gen=None,
        db_manager=None,
        vector_db=None,
        scenes_data=None,
        image_service=None,
        tts_service=None,
    ):
        self.text_gen = text_gen
        self.db_manager = db_manager
        self.scenes_data = scenes_data or {}
        self.image_service = image_service
        self.tts_service = tts_service

        # 初始化所有 Agent
        self.director = DirectorAgent(text_gen=text_gen, db_manager=db_manager)
        self.emotion = EmotionAgent()
        self.world = WorldSimulator(scenes_data=scenes_data)
        self.event = EventAgent()
        self.consistency = ConsistencyAgent()
        self.dialogue = DialogueAgent(text_gen=text_gen)

        # 记忆管理器
        self.memory = MemoryManager(vector_db=vector_db)

        # 多会话状态隔离：thread_id → AgentState
        self._states: Dict[str, AgentState] = {}
        self._lock = threading.Lock()

    @property
    def state(self) -> Optional[AgentState]:
        """向后兼容：返回任意一个活跃状态（仅用于调试/单会话场景）"""
        with self._lock:
            return next(iter(self._states.values()), None)

    async def init_session(
        self,
        thread_id: str,
        character_id: int,
        character_name: str = "",
        character_personality: Dict = None,
        initial_scene: str = "classroom",
        initial_states: Dict[str, float] = None,
    ) -> AgentState:
        """初始化新会话"""
        state = AgentState(
            thread_id=thread_id,
            character_id=character_id,
            character_name=character_name,
            character_personality=character_personality or {},
            world=WorldState(current_scene=initial_scene),
        )

        # 加载初始情绪状态
        if initial_states:
            for key, value in initial_states.items():
                if hasattr(state.emotion, key):
                    setattr(state.emotion, key, float(value))

        with self._lock:
            self._states[thread_id] = state

        logger.info(f"会话初始化: thread_id={thread_id}, character={character_name}")
        return state

    async def process_input(self, user_input: str, thread_id: str = None) -> Dict[str, Any]:
        """处理玩家输入 → 返回完整场景输出

        流程：Director → World → Emotion → Event → Dialogue → Consistency

        Args:
            user_input: 玩家输入文本
            thread_id: 会话ID（多会话隔离必需）
        """
        if thread_id is None:
            # 向后兼容：单会话模式
            state = self.state
            if not state:
                raise RuntimeError("未初始化会话，请先调用 init_session()")
        else:
            with self._lock:
                state = self._states.get(thread_id)
            if not state:
                raise RuntimeError(f"会话 {thread_id} 未初始化，请先调用 init_session()")
        state.last_player_input = user_input
        state.advance_round()
        state.add_to_history("player", user_input)

        # 1. Director: 决定剧情走向
        director_result = await self.director.think(state)
        if director_result.get("action") == "end_game":
            return await self._build_ending_output(state)

        # 2. World: 推进世界状态
        world_result = await self.world.think(state)
        state.output_scene = world_result.get("scene", state.world.current_scene)

        # 3. Emotion: 计算情绪变化
        emotion_result = await self.emotion.think(state)
        state.output_emotion_changes = emotion_result.get("state_changes", {})

        # 4. Event: 选择事件
        event_result = await self.event.think(state)
        if event_result.get("event"):
            state.pending_event = event_result["event"]

        # 5. Dialogue: 生成角色台词
        dialogue_result = await self.dialogue.think(state)
        character_dialogue = dialogue_result.get("character_dialogue", "")
        state.output_dialogue = character_dialogue
        state.add_to_history("character", character_dialogue)

        # 6. Consistency: 输出前校验
        consistency_result = await self.consistency.think(state)

        # 保存事件摘要到记忆
        if state.pending_event:
            self.memory.add_event(
                character_id=state.character_id,
                event_summary=f"{state.pending_event.get('type')}: {state.pending_event.get('description')}",
            )
            state.event_history.append(state.pending_event)

        # 构建输出
        output = {
            "thread_id": state.thread_id,
            "character_dialogue": character_dialogue,
            "player_options": state.output_options,
            "scene": state.output_scene,
            "current_states": state.emotion.to_dict(),
            "state_changes": state.output_emotion_changes,
            "pad": emotion_result.get("pad", {}),
            "phase": state.phase.value,
            "elapsed_minutes": round(state.world.elapsed_minutes, 1),
            "weather": state.world.weather,
            "current_time": state.world.current_time,
            "round": state.round_count,
            "consistency": consistency_result,
            "is_game_finished": state.phase == SessionPhase.ENDING,
            "event_type": state.pending_event.get("type") if state.pending_event else None,
            "event_description": state.pending_event.get("description") if state.pending_event else None,
            "emotion_tags": self._get_emotion_tags(state),
        }

        logger.info(f"输入处理完成: round={state.round_count}, phase={state.phase.value}")
        return output

    async def _build_ending_output(self, state: AgentState = None) -> Dict[str, Any]:
        """构建结局输出"""
        if state is None:
            state = self.state
        ending_text = self._generate_ending_text(state)
        state.add_to_history("character", ending_text)

        return {
            "thread_id": state.thread_id,
            "character_dialogue": ending_text,
            "player_options": [],
            "scene": state.output_scene,
            "current_states": state.emotion.to_dict(),
            "state_changes": {},
            "pad": state.emotion.pad_vector(),
            "phase": "ending",
            "elapsed_minutes": round(state.world.elapsed_minutes, 1),
            "weather": state.world.weather,
            "current_time": state.world.current_time,
            "round": state.round_count,
            "consistency": {"passed": True, "violations": []},
            "is_game_finished": True,
            "event_type": "ending",
            "event_description": "故事到达结局",
            "emotion_tags": self._get_emotion_tags(state),
        }

    def _generate_ending_text(self, state: AgentState = None) -> str:
        """生成结局文本"""
        if state is None:
            state = self.state
        name = state.character_name or "角色"
        emotion = state.emotion
        if emotion.favorability >= 70:
            return f"{name}: 谢谢你...我永远不会忘记今天的。"
        elif emotion.favorability >= 40:
            return f"{name}: 今天就这样吧。再见。"
        else:
            return f"{name}: ...（转身离去，没有回头）"

    def _get_emotion_tags(self, state: AgentState) -> str:
        """获取情绪语义标签"""
        e = state.emotion
        tags = []
        if e.emotion >= 70:
            tags.append("情绪高涨")
        elif e.emotion >= 40:
            tags.append("情绪稳定")
        else:
            tags.append("情绪低落")
        if e.favorability >= 70:
            tags.append("好感度高")
        if e.trust >= 70:
            tags.append("信任度高")
        if e.stress >= 60:
            tags.append("压力大")
        if e.happiness >= 70:
            tags.append("快乐")
        elif e.sadness >= 60:
            tags.append("悲伤")
        return " ".join(tags) if tags else "情绪稳定"
