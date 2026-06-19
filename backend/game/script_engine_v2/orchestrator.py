"""Orchestrator V2 — 流水线调度员

职责：
  - 记忆读写（Redis/PG）
  - 流水线编排（调用各组件）
  - TTS 语音合成（异步）
  - 图片查询（异步）
  - 事件压缩（事件结束时）
  - 输出构建

不负责：
  - 任何"思考"逻辑（ScriptEngine 的职责）
  - 任何"计算"逻辑（WorldSimulator 的职责）
"""
import asyncio
import json
import threading
import time
from typing import Dict, Any, Optional
from .engine import ScriptEngine
from .world_simulator import WorldSimulator
from .consistency_agent import ConsistencyAgent
from .llm_tool import LLMTool
from .models import RoundOutput, Option
from utils.logger import get_logger

logger = get_logger("orchestrator_v2")

# 导入记忆存储（从旧模块复用）
import sys
import os
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from game.agents.redis_memory import RedisMemoryStore
from game.agents.pg_memory import PgMemoryStore
from game.agents.state import AgentState, EmotionState, WorldState, SessionPhase


class OrchestratorV2:
    """Orchestrator V2 — 流水线调度员

    数据流：
    Redis 加载 → ScriptEngine → WorldSimulator → ConsistencyAgent → Redis 写回
    """

    def __init__(
        self,
        text_gen=None,
        db_manager=None,
        redis_client=None,
        scenes_data=None,
        image_service=None,
        tts_service=None,
    ):
        # 核心组件
        llm_tool = LLMTool(text_gen) if text_gen else None
        self.script_engine = ScriptEngine(llm_tool=llm_tool, scenes_data=scenes_data)
        self.world_simulator = WorldSimulator()
        self.consistency = ConsistencyAgent(llm_tool=llm_tool)

        # 记忆存储
        self.redis_store = RedisMemoryStore(redis_client) if redis_client else None
        self.pg_store = PgMemoryStore(db_manager) if db_manager else None

        # 外部服务
        self.image_service = image_service
        self.tts_service = tts_service

        # TTS 情感引擎
        self._tts_emotion_available = False
        try:
            from services.tts_emotion_engine import calculate_tts_params, extract_personality_keywords
            self._calculate_tts_params = calculate_tts_params
            self._extract_personality_keywords = extract_personality_keywords
            self._tts_emotion_available = True
        except ImportError:
            pass

        # 多会话状态
        self._states: Dict[str, AgentState] = {}
        self._lock = threading.Lock()

    async def init_session(
        self,
        thread_id: str,
        character_id: int,
        character_name: str = "",
        character_personality: dict = None,
        initial_scene: str = "classroom",
        initial_states: dict = None,
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
            state.used_event_ids = set(narrative.get("used_events", []))

        # 加载当前事件
        current_event = redis_data.get("current_event", {})
        if current_event and current_event.get("type"):
            state.pending_event = current_event

    async def _save_to_redis(self, state: AgentState, player_input: str, dialogue: str):
        """保存本轮数据到 Redis"""
        if not self.redis_store:
            return

        self.redis_store.save_round(
            thread_id=state.thread_id,
            player_input=player_input,
            character_dialogue=dialogue,
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
            return

        # 2. LLM 压缩为事件摘要
        summary = await self._compress_event(working_memory, state)

        # 3. 计算情绪变化
        emotion_start = event_data.get("emotion_snapshot", {})
        emotion_end = state.emotion.to_dict()

        # 4. 存入 PostgreSQL
        self.pg_store.save_event(
            character_id=state.character_id,
            thread_id=state.thread_id,
            event_data={
                "event_type": state.pending_event.get("type") if state.pending_event else "unknown",
                "event_summary": summary,
                "scene": state.world.current_scene,
                "emotion_start": emotion_start,
                "emotion_end": emotion_end,
                "round_count": len(working_memory) // 2,
                "world_state": {
                    "current_scene": state.world.current_scene,
                    "current_time": state.world.current_time,
                    "weather": state.world.weather,
                },
                "game_round_start": state.total_rounds - len(working_memory) // 2,
                "game_round_end": state.total_rounds,
            },
        )

        # 5. 更新 state.event_summaries
        state.event_summaries.append(summary)
        if len(state.event_summaries) > 5:
            state.event_summaries = state.event_summaries[-5:]

        # 6. 清理 Redis 事件数据
        self.redis_store.clear_event_data(state.thread_id)

        # 7. 添加到事件历史
        state.event_history.append({
            "type": state.pending_event.get("type") if state.pending_event else "unknown",
            "summary": summary,
        })

        logger.info(f"事件结束处理完成")

    async def _compress_event(self, working_memory: list, state: AgentState) -> str:
        """LLM 压缩事件为摘要"""
        llm_tool = self.script_engine.llm
        if not llm_tool:
            return self._fallback_compress(working_memory, state)

        dialogue_text = ""
        for msg in working_memory:
            role = "玩家" if msg.get("role") == "player" else state.character_name
            dialogue_text += f"{role}: {msg.get('content', '')}\n"

        prompt = f"""请将以下对话压缩为 100-200 字的事件摘要。

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
            result = await llm_tool.generate(prompt, max_tokens=250, call_type="story")
            if result and len(result) > 20:
                return result.strip()
        except Exception as e:
            logger.warning(f"LLM 压缩失败: {e}")

        return self._fallback_compress(working_memory, state)

    def _fallback_compress(self, working_memory: list, state: AgentState) -> str:
        """降级压缩"""
        recent = working_memory[-4:] if len(working_memory) >= 4 else working_memory
        lines = []
        for msg in recent:
            role = "玩家" if msg.get("role") == "player" else "角色"
            lines.append(f"{role}: {msg.get('content', '')[:30]}")
        return "对话摘要: " + " | ".join(lines)

    def _generate_tts(self, state: AgentState, dialogue: str):
        """生成 TTS（异步）"""
        if not self.tts_service or not self.tts_service.enabled:
            return None
        if not dialogue:
            return None

        try:
            emotion_params = None
            if self._tts_emotion_available:
                personality_keywords = self._extract_personality_keywords(
                    state.character_personality
                )
                tts_params = self._calculate_tts_params(
                    state.emotion,
                    personality_keywords=personality_keywords,
                )
                emotion_params = {
                    "emotion": tts_params.emotion,
                    "speed": tts_params.speed_ratio,
                    "pitch": tts_params.pitch_ratio,
                    "volume": tts_params.volume_ratio,
                }

            loop = asyncio.get_running_loop()
            return loop.run_in_executor(
                None,
                lambda: self.tts_service.generate_speech(
                    text=dialogue,
                    character_id=state.character_id,
                    emotion_params=emotion_params,
                ),
            )
        except Exception as e:
            logger.warning(f"TTS 提交失败: {e}")
            return None

    async def process_input(self, user_input: str, thread_id: str = None) -> Dict[str, Any]:
        """主流程：处理玩家输入

        流程：Redis 加载 → ScriptEngine → WorldSimulator → Consistency → Redis 写回
        """
        # 获取状态
        if thread_id is None:
            state = next(iter(self._states.values()), None)
            if not state:
                raise RuntimeError("未初始化会话")
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

        # Step 3: ScriptEngine 生成交互数据
        output = await self.script_engine.generate_round(state)

        # Step 4: WorldSimulator 执行
        self.world_simulator.advance_time(state.world, output.phase)
        self.world_simulator.update_weather(state.total_rounds, state.world)
        self.world_simulator.apply_decay(state.emotion)

        # Step 5: 更新场景
        state.output_scene = output.scene
        if output.scene != state.world.current_scene:
            state.world.current_scene = output.scene

        # Step 6: ConsistencyAgent 校验
        consistency_result = await self.consistency.check(
            state, output.character_dialogue, state.output_emotion_changes
        )

        # Step 7: TTS（异步）
        tts_future = self._generate_tts(state, output.character_dialogue)

        # Step 8: 写回 Redis
        await self._save_to_redis(state, user_input, output.character_dialogue)

        # Step 9: 事件结束处理
        if output.event_ended:
            await self._handle_event_end(state)
            state.event_round_count = 0

        # Step 10: 获取场景图片URL
        scene_image_url = None
        composite_image_url = None
        try:
            from api.services.image.image_service import ImageService
            image_service = ImageService()
            if image_service.enabled and output.scene:
                scene_image_url = image_service.get_scene_image_url(output.scene)
        except Exception as e:
            logger.debug(f"获取场景图片失败（非致命）: {e}")

        # Step 11: 构建响应
        response = {
            "thread_id": thread_id,
            "character_dialogue": output.character_dialogue,
            "player_options": [
                {"id": o.id, "text": o.text, "direction": o.direction}
                for o in output.player_options
            ],
            "scene": output.scene,
            "scene_image_url": scene_image_url,
            "composite_image_url": composite_image_url,
            "current_states": state.emotion.to_dict(),
            "state_changes": state.output_emotion_changes,
            "phase": output.phase,
            "elapsed_minutes": round(state.world.elapsed_minutes, 1),
            "weather": state.world.weather,
            "current_time": state.world.current_time,
            "round": state.total_rounds,
            "is_game_finished": output.is_game_finished,
            "ending_type": output.ending_type,
            "event_type": output.event_type,
            "event_description": output.event_description,
            "consistency": consistency_result,
            "engine": "script_engine_v2",
        }

        # 等待 TTS
        if tts_future:
            try:
                tts_result = await asyncio.wait_for(tts_future, timeout=5.0)
                if tts_result:
                    response["audio_url"] = tts_result.get("audio_url")
                    response["audio_duration"] = tts_result.get("duration", 0.0)
            except (asyncio.TimeoutError, Exception):
                pass

        return response

    async def process_input_with_option(self, thread_id: str, option_id: int) -> Dict[str, Any]:
        """处理玩家选择选项

        Args:
            thread_id: 会话 ID
            option_id: 选项 ID
        """
        with self._lock:
            state = self._states.get(thread_id)
        if not state:
            raise RuntimeError(f"会话 {thread_id} 未初始化")

        # 查找选项
        option = None
        for o in (state.output_options or []):
            if o.id == option_id:
                option = o
                break

        if option:
            # 应用数值变化
            changes = self.script_engine.apply_option_changes(state, option)
            state.output_emotion_changes = changes

        # 调用主流程
        return await self.process_input(
            user_input=option.text if option else f"option:{option_id}",
            thread_id=thread_id
        )

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
