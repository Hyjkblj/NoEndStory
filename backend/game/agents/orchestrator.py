"""AgentOrchestrator — 顺序状态机，串联所有 Agent

记忆架构:
  短期记忆 (Redis): 单个事件内的对话历史、情绪快照、世界状态
  长期记忆 (PostgreSQL): 事件摘要、角色知识、玩家偏好

数据流:
  Redis 加载 → Agent 流水线 → Redis 写回 → 事件结束时压缩到 PG
"""
import asyncio
import json
import threading
import time
from typing import Dict, Any, Optional, Callable
from .base import BaseAgent
from .state import AgentState, SessionPhase, WorldState, EmotionState
from .director_agent import DirectorAgent
from .emotion_agent import EmotionAgent
from .world_simulator import WorldSimulator
from .event_agent import EventAgent
from .consistency_agent import ConsistencyAgent
from .dialogue_agent import DialogueAgent
from .redis_memory import RedisMemoryStore
from .pg_memory import PgMemoryStore
from utils.logger import get_logger
from services.tts_emotion_engine import calculate_tts_params, extract_personality_keywords
import config

logger = get_logger("orchestrator")


class AgentOrchestrator:
    """Agent 编排器：顺序状态机 + Redis/PG 双层记忆

    数据流：
    Redis 加载 → Director → World → Emotion → Event → Dialogue → TTS
    → Consistency → Redis 写回 → [事件结束] → 压缩到 PG

    支持多会话并发：每个 thread_id 拥有独立的 AgentState。
    """

    def __init__(
        self,
        text_gen=None,
        db_manager=None,
        redis_client=None,
        vector_db=None,  # 保留参数兼容，不再使用
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

        # 记忆存储
        self.redis_store = RedisMemoryStore(redis_client) if redis_client else None
        self.pg_store = PgMemoryStore(db_manager) if db_manager else None

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

        # 初始化 Redis 短期记忆
        if self.redis_store:
            self.redis_store.init_session(
                thread_id=thread_id,
                character_id=character_id,
                character_name=character_name,
                emotion_snapshot=state.emotion.to_dict(),
                world_state=state.world.__dict__,
            )

        # 加载 PostgreSQL 长期记忆
        if self.pg_store:
            recent_events = self.pg_store.get_recent_events(character_id, n=3)
            state.event_summaries = [e["event_summary"] for e in recent_events]
            state.knowledge = self.pg_store.get_knowledge(character_id, limit=10)
            state.preferences = self.pg_store.get_preferences(character_id)

        with self._lock:
            self._states[thread_id] = state

        logger.info(f"会话初始化: thread_id={thread_id}, character={character_name}")
        return state

    async def _load_from_redis(self, state: AgentState):
        """从 Redis 加载记忆到 AgentState"""
        if not self.redis_store:
            return

        redis_data = self.redis_store.load_all(state.thread_id)
        if not redis_data:
            logger.warning(f"Redis 无数据: {state.thread_id}")
            return

        # 加载对话历史
        state.dialogue_history = redis_data.get("working_memory", [])

        # 加载情绪状态
        emotion_data = redis_data.get("emotion_snapshot", {})
        if emotion_data:
            for key, value in emotion_data.items():
                if hasattr(state.emotion, key):
                    setattr(state.emotion, key, float(value))

        # 加载世界状态
        world_data = redis_data.get("world_state", {})
        if world_data:
            for key, value in world_data.items():
                if hasattr(state.world, key):
                    setattr(state.world, key, value)

        # 加载叙事状态
        narrative = redis_data.get("narrative_state", {})
        if narrative:
            state.total_rounds = narrative.get("total_rounds", 0)
            state.round_count = narrative.get("round_count", 0)
            phase_str = narrative.get("phase", "opening")
            try:
                state.phase = SessionPhase(phase_str)
            except ValueError:
                state.phase = SessionPhase.OPENING
            state.used_event_ids = set(narrative.get("used_events", []))

        # 加载当前事件
        current_event = redis_data.get("current_event", {})
        if current_event and current_event.get("type"):
            state.pending_event = current_event

    async def _save_to_redis(self, state: AgentState, player_input: str, character_dialogue: str):
        """保存本轮数据到 Redis"""
        if not self.redis_store:
            return

        self.redis_store.save_round(
            thread_id=state.thread_id,
            player_input=player_input,
            character_dialogue=character_dialogue,
            emotion_snapshot=state.emotion.to_dict(),
            world_state={
                "current_scene": state.world.current_scene,
                "current_time": state.world.current_time,
                "weather": state.world.weather,
                "elapsed_minutes": state.world.elapsed_minutes,
                "time_of_day_progress": state.world.time_of_day_progress,
            },
            narrative_state={
                "phase": state.phase.value if state.phase else "opening",
                "total_rounds": state.total_rounds,
                "round_count": state.round_count,
                "current_event_type": state.pending_event.get("type") if state.pending_event else None,
                "current_beat_name": state.current_beat.name if state.current_beat else None,
                "used_events": list(state.used_event_ids),
            },
        )

    async def _handle_event_end(self, state: AgentState):
        """事件结束处理：从 Redis 加载 → LLM 压缩 → 存入 PG"""
        if not self.redis_store or not self.pg_store:
            return

        # 1. 从 Redis 加载完整事件数据
        event_data = self.redis_store.load_event_data(state.thread_id)
        working_memory = event_data.get("working_memory", [])

        if not working_memory:
            logger.warning("事件结束但无对话数据")
            return

        # 2. LLM 压缩为事件摘要
        summary = await self._compress_event(working_memory, state)

        # 3. 计算情绪变化
        emotion_start = event_data.get("emotion_snapshot", {})
        emotion_end = state.emotion.to_dict()
        emotion_delta = {}
        for key in emotion_start:
            if key in emotion_end:
                delta = emotion_end[key] - emotion_start[key]
                if abs(delta) > 0.1:
                    emotion_delta[key] = round(delta, 1)

        # 4. 提取玩家选择
        player_choices = []
        for msg in working_memory:
            if msg.get("role") == "player":
                player_choices.append({
                    "round": msg.get("round"),
                    "choice": msg.get("content", "")[:50],
                })

        # 5. 存入 PostgreSQL
        event_id = self.pg_store.save_event(
            character_id=state.character_id,
            thread_id=state.thread_id,
            event_data={
                "event_type": state.pending_event.get("type") if state.pending_event else "unknown",
                "event_summary": summary,
                "scene": state.world.current_scene,
                "emotion_start": emotion_start,
                "emotion_end": emotion_end,
                "emotion_delta": emotion_delta,
                "round_count": len(working_memory) // 2,
                "player_choices": player_choices,
                "world_state": {
                    "current_scene": state.world.current_scene,
                    "current_time": state.world.current_time,
                    "weather": state.world.weather,
                },
                "game_round_start": state.total_rounds - len(working_memory) // 2,
                "game_round_end": state.total_rounds,
            },
        )

        # 6. 更新 state.event_summaries
        state.event_summaries.append(summary)
        if len(state.event_summaries) > 5:
            state.event_summaries = state.event_summaries[-5:]

        # 7. 清理 Redis 事件数据
        self.redis_store.clear_event_data(state.thread_id)

        # 8. 添加到事件历史
        state.event_history.append({
            "type": state.pending_event.get("type") if state.pending_event else "unknown",
            "summary": summary,
            "event_id": event_id,
        })

        logger.info(f"事件结束处理完成: type={state.pending_event.get('type') if state.pending_event else 'unknown'}")

    async def _compress_event(self, working_memory: list, state: AgentState) -> str:
        """LLM 压缩事件为摘要"""
        if not self.text_gen:
            return self._fallback_compress(working_memory)

        # 构建压缩 prompt
        dialogue_text = ""
        for msg in working_memory:
            role = "玩家" if msg.get("role") == "player" else state.character_name
            dialogue_text += f"{role}: {msg.get('content', '')}\n"

        prompt = f"""请将以下对话压缩为 100-200 字的事件摘要，保留关键情节和情感变化。

角色：{state.character_name}
场景：{state.world.current_scene}

对话内容：
{dialogue_text}

要求：
1. 用第三人称描述
2. 保留关键情节点
3. 记录情感变化趋势
4. 100-200 字"""

        try:
            from llm.call_config import get_call_params
            p = get_call_params("story")
            result = self.text_gen._call_text_generation(
                prompt, max_tokens=250, temperature=0.7, call_type="story"
            )
            if result and len(result) > 20:
                return result.strip()
        except Exception as e:
            logger.warning(f"LLM 压缩失败: {e}")

        return self._fallback_compress(working_memory)

    def _fallback_compress(self, working_memory: list) -> str:
        """降级压缩：取最后 2 轮对话"""
        recent = working_memory[-4:] if len(working_memory) >= 4 else working_memory
        lines = []
        for msg in recent:
            role = "玩家" if msg.get("role") == "player" else "角色"
            lines.append(f"{role}: {msg.get('content', '')[:30]}")
        return "对话摘要: " + " | ".join(lines)

    def _is_event_ended(self, state: AgentState) -> bool:
        """判断事件是否结束（基于轮次数）"""
        min_rounds = 2
        max_rounds = 5

        if state.round_count < min_rounds:
            return False
        if state.round_count >= max_rounds:
            return True

        # 渐进式结束概率
        import random
        if state.round_count >= 3:
            prob = (state.round_count - 2) * 0.3
            return random.random() < prob

        return False

    async def process_input(self, user_input: str, thread_id: str = None) -> Dict[str, Any]:
        """处理玩家输入 → 返回完整场景输出

        流程：Redis 加载 → Director → World → Emotion → Event → Dialogue
        → TTS → Consistency → Redis 写回 → [事件结束] → 压缩到 PG
        """
        if thread_id is None:
            state = self.state
            if not state:
                raise RuntimeError("未初始化会话，请先调用 init_session()")
        else:
            with self._lock:
                state = self._states.get(thread_id)
            if not state:
                raise RuntimeError(f"会话 {thread_id} 未初始化")

        # Step 1: 从 Redis 加载记忆
        await self._load_from_redis(state)

        # Step 2: 记录玩家输入
        state.last_player_input = user_input
        state.advance_round()
        state.add_to_history("player", user_input)

        # Step 3: Director — 决定剧情走向
        director_result = await self.director.think(state)
        if director_result.get("action") == "end_game":
            return await self._build_ending_output(state)

        # Step 4: World — 推进世界状态
        world_result = await self.world.think(state)
        state.output_scene = world_result.get("scene", state.world.current_scene)

        # Step 5: Emotion — 计算情绪变化
        emotion_result = await self.emotion.think(state)
        state.output_emotion_changes = emotion_result.get("state_changes", {})

        # Step 6: Event — 选择事件
        event_result = await self.event.think(state)
        if event_result.get("event"):
            state.pending_event = event_result["event"]
            if self.redis_store:
                self.redis_store.save_current_event(state.thread_id, state.pending_event)

        # Step 7: Dialogue — 生成角色台词
        dialogue_result = await self.dialogue.think(state)
        character_dialogue = dialogue_result.get("character_dialogue", "")
        state.output_dialogue = character_dialogue
        state.add_to_history("character", character_dialogue)

        # Step 8: Image & TTS（异步，不阻塞）
        tts_future = None
        if self.tts_service and self.tts_service.enabled and character_dialogue:
            try:
                personality_keywords = extract_personality_keywords(state.character_personality)
                tts_params = calculate_tts_params(
                    state.emotion,
                    personality_keywords=personality_keywords,
                    confidence_threshold=config.TTS_EMOTION_CONFIDENCE_THRESHOLD,
                )
                state.output_tts_params = tts_params
                emotion_params = {
                    "emotion": tts_params.emotion,
                    "speed": tts_params.speed_ratio,
                    "pitch": tts_params.pitch_ratio,
                    "volume": tts_params.volume_ratio,
                }
                loop = asyncio.get_running_loop()
                tts_future = loop.run_in_executor(
                    None,
                    lambda: self.tts_service.generate_speech(
                        text=character_dialogue,
                        character_id=state.character_id,
                        emotion_params=emotion_params,
                    ),
                )
            except Exception as e:
                logger.warning(f"TTS 提交失败: {e}")

        # Step 9: Consistency — 输出前校验
        consistency_result = await self.consistency.think(state)

        # Step 10: 写回 Redis
        await self._save_to_redis(state, user_input, character_dialogue)

        # Step 11: 检查事件是否结束
        event_ended = self._is_event_ended(state)
        if event_ended:
            await self._handle_event_end(state)
            state.round_count = 0  # 重置事件内轮次

        # Step 12: 构建输出
        output = {
            "character_dialogue": character_dialogue,
            "player_options": dialogue_result.get("player_options", []),
            "scene": state.output_scene,
            "current_states": state.emotion.to_dict(),
            "state_changes": state.output_emotion_changes,
            "phase": state.phase.value if state.phase else "unknown",
            "elapsed_minutes": round(state.world.elapsed_minutes, 1),
            "weather": state.world.weather,
            "current_time": state.world.current_time,
            "round": state.total_rounds,
            "is_game_finished": False,
            "event_type": state.pending_event.get("type") if state.pending_event else None,
            "event_description": state.pending_event.get("description") if state.pending_event else None,
            "consistency": consistency_result,
            "event_ended": event_ended,
        }

        # 等待 TTS 完成
        if tts_future:
            try:
                tts_result = await asyncio.wait_for(tts_future, timeout=5.0)
                if tts_result:
                    output["audio_url"] = tts_result.get("audio_url")
                    output["audio_duration"] = tts_result.get("duration", 0.0)
            except asyncio.TimeoutError:
                logger.warning("TTS 超时")
            except Exception as e:
                logger.warning(f"TTS 失败: {e}")

        return output

    async def _build_ending_output(self, state: AgentState) -> Dict[str, Any]:
        """构建结局输出"""
        ending_text = self._generate_ending_text(state)

        # 保存结局到 PG
        if self.pg_store:
            await self._handle_event_end(state)

        return {
            "character_dialogue": ending_text,
            "player_options": [],
            "scene": state.output_scene or state.world.current_scene,
            "current_states": state.emotion.to_dict(),
            "state_changes": {},
            "phase": "ending",
            "elapsed_minutes": round(state.world.elapsed_minutes, 1),
            "weather": state.world.weather,
            "current_time": state.world.current_time,
            "round": state.total_rounds,
            "is_game_finished": True,
            "event_type": "ending",
            "event_description": "故事结束",
            "consistency": {"passed": True, "violations": [], "severity": "ok"},
        }

    def _generate_ending_text(self, state: AgentState) -> str:
        """生成结局文本"""
        name = state.character_name or "角色"
        emotion = state.emotion

        if emotion.favorability >= 70:
            return f"{name}: 谢谢你...我永远不会忘记今天的。"
        elif emotion.favorability >= 40:
            return f"{name}: 今天就这样吧。再见。"
        else:
            return f"{name}: ...（转身离去，没有回头）"

    def _get_emotion_tags(self, emotion: EmotionState) -> str:
        """获取情绪标签"""
        tags = []
        if emotion.favorability >= 70:
            tags.append("喜欢")
        elif emotion.favorability <= 30:
            tags.append("冷淡")
        if emotion.happiness >= 70:
            tags.append("开心")
        elif emotion.sadness >= 60:
            tags.append("难过")
        if emotion.hostility >= 50:
            tags.append("敌意")
        if emotion.stress >= 60:
            tags.append("压力")
        return ",".join(tags) if tags else "平静"

    def _sync_bridge(self, state: AgentState) -> Dict[str, Any]:
        """同步桥梁：将 AgentState 转为 NOS Agent 格式"""
        return {
            "favorability": state.emotion.favorability,
            "trust": state.emotion.trust,
            "hostility": state.emotion.hostility,
            "happiness": state.emotion.happiness,
            "sadness": state.emotion.sadness,
        }

    def get_session_state(self, thread_id: str) -> Optional[AgentState]:
        """获取会话状态"""
        with self._lock:
            return self._states.get(thread_id)

    def cleanup_session(self, thread_id: str):
        """清理会话"""
        with self._lock:
            self._states.pop(thread_id, None)
        if self.redis_store:
            self.redis_store.delete_session(thread_id)
        logger.info(f"会话清理: {thread_id}")
