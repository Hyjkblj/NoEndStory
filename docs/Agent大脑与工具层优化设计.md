# Agent 大脑与工具层优化设计

> 适配 Redis/PG 双层记忆架构，升级 6 个 Agent 的推理能力和工具集成
> 更新日期: 2026-06-18

---

## 一、设计原则

```
1. 大脑负责推理，工具负责执行
   → Agent 只做决策，不直接调用外部服务
   → 通过工具接口访问数据库、LLM、向量检索等

2. 记忆驱动决策
   → 每个 Agent 的决策都基于记忆层的数据
   → 短期记忆（Redis）提供即时上下文
   → 长期记忆（PG）提供历史参考

3. LLM 增强而非替代规则
   → 规则引擎处理确定性逻辑（时间推进、情绪衰减）
   → LLM 处理创造性任务（台词生成、事件压缩）
   → 降级方案：LLM 失败时回退到规则

4. 工具标准化
   → 所有工具继承 BaseTool 抽象类
   → 统一的输入/输出格式
   → 统一的错误处理和日志
```

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      AgentOrchestrator                           │
│  编排: 记忆加载 → Agent 流水线 → 记忆写回 → 事件压缩           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    大脑层 (Brain)                         │   │
│  │  每个 Agent 的推理逻辑（规则 + LLM）                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    工具层 (Tools)                         │   │
│  │  LLMTool / DBTool / VectorTool / TTSTool / ImageTool    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    记忆层 (Memory)                        │   │
│  │  RedisMemoryStore (短期) + PgMemoryStore (长期)          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、工具层设计

### 3.1 BaseTool 抽象基类

```python
class BaseTool:
    """工具基类"""

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"tool.{name}")

    async def execute(self, **kwargs) -> Any:
        """执行工具"""
        raise NotImplementedError

    def validate_input(self, **kwargs) -> bool:
        """校验输入"""
        return True
```

### 3.2 工具清单

| 工具 | 用途 | 调用者 | 延迟 |
|------|------|--------|------|
| **LLMTool** | LLM 推理和生成 | DialogueAgent, Orchestrator | 1-3s |
| **MemoryTool** | 读写 Redis/PG 记忆 | Orchestrator, EmotionAgent | <10ms |
| **EventTool** | 事件选择和构建 | EventAgent, DirectorAgent | <5ms |
| **SceneTool** | 场景查询和切换 | WorldSimulator | <5ms |
| **EmotionTool** | 情绪计算和衰减 | EmotionAgent | <1ms |
| **TTSTool** | 语音合成 | Orchestrator | 1-3s（异步） |
| **ImageTool** | 图片查询 | Orchestrator | <10ms |

### 3.3 各工具实现

#### LLMTool

```python
class LLMTool(BaseTool):
    """LLM 推理工具"""

    def __init__(self, text_gen):
        super().__init__("llm")
        self.text_gen = text_gen

    async def generate(self, prompt: str, max_tokens: int = 200,
                       temperature: float = 0.7, call_type: str = "default") -> str:
        """生成文本"""
        from llm.call_config import get_call_params
        p = get_call_params(call_type)
        result = self.text_gen._call_text_generation(
            prompt, max_tokens=p.max_tokens or max_tokens,
            temperature=p.temperature or temperature, call_type=call_type
        )
        return result or ""

    async def generate_stream(self, prompt: str, max_tokens: int = 200,
                              temperature: float = 0.7, on_token: Callable = None):
        """流式生成"""
        from llm.call_config import get_call_params
        p = get_call_params("dialogue")
        for chunk in self.text_gen.generate_dialogue_stream(
            prompt, max_tokens=p.max_tokens, temperature=p.temperature
        ):
            if on_token:
                on_token(chunk)
            yield chunk

    async def compress(self, text: str, max_chars: int = 200) -> str:
        """压缩文本为摘要"""
        prompt = f"请将以下内容压缩为{max_chars}字以内的摘要：\n\n{text}"
        return await self.generate(prompt, max_tokens=max_chars // 2, call_type="story")
```

#### MemoryTool

```python
class MemoryTool(BaseTool):
    """记忆读写工具"""

    def __init__(self, redis_store: RedisMemoryStore, pg_store: PgMemoryStore):
        super().__init__("memory")
        self.redis = redis_store
        self.pg = pg_store

    # === 短期记忆（Redis）===
    async def load_session(self, thread_id: str) -> dict:
        """加载会话记忆"""
        return self.redis.load_all(thread_id)

    async def save_round(self, thread_id: str, **kwargs):
        """保存一轮对话"""
        self.redis.save_round(thread_id, **kwargs)

    async def save_emotion(self, thread_id: str, emotion: dict):
        """保存情绪快照"""
        self.redis.save_emotion_snapshot(thread_id, emotion)

    async def save_world(self, thread_id: str, world: dict):
        """保存世界状态"""
        self.redis.save_world_state(thread_id, world)

    # === 长期记忆（PG）===
    async def load_recent_events(self, character_id: int, n: int = 5) -> list:
        """加载最近事件"""
        return self.pg.get_recent_events(character_id, n)

    async def load_knowledge(self, character_id: int, limit: int = 10) -> list:
        """加载角色知识"""
        return self.pg.get_knowledge(character_id, limit=limit)

    async def load_preferences(self, character_id: int) -> list:
        """加载玩家偏好"""
        return self.pg.get_preferences(character_id)

    async def save_event(self, character_id: int, thread_id: str, event_data: dict) -> int:
        """保存事件"""
        return self.pg.save_event(character_id, thread_id, event_data)

    async def save_knowledge(self, character_id: int, knowledge_type: str,
                             content: str, importance: float = 0.5) -> bool:
        """保存角色知识"""
        return self.pg.save_knowledge(character_id, knowledge_type, content, importance)

    async def update_preference(self, character_id: int, preference_type: str,
                                preference_value: dict) -> bool:
        """更新玩家偏好"""
        return self.pg.update_preference(character_id, preference_type, preference_value)
```

#### EmotionTool

```python
class EmotionTool(BaseTool):
    """情绪计算工具"""

    def __init__(self):
        super().__init__("emotion")

    def apply_decay(self, emotion: EmotionState) -> EmotionState:
        """情绪衰减"""
        decay_rates = {
            "stress": 0.15, "anxiety": 0.10, "emotion": 0.05,
            "happiness": 0.03, "sadness": 0.08,
        }
        for key, rate in decay_rates.items():
            current = getattr(emotion, key)
            setattr(emotion, key, max(0.0, current * (1 - rate)))
        return emotion

    def analyze_keywords(self, text: str) -> dict:
        """关键词分析（降级方案）"""
        changes = {"favorability": 0, "trust": 0, "happiness": 0,
                   "stress": 0, "confidence": 0}
        positive = {"谢谢", "喜欢", "好的", "可以", "真棒", "开心", "爱你", "支持"}
        negative = {"讨厌", "不喜欢", "不行", "滚", "烦", "无聊", "恨", "失望"}
        supportive = {"我相信你", "你可以", "加油", "相信", "信任"}

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

        return {k: max(-10.0, min(10.0, v)) for k, v in changes.items()}

    def calculate_pad(self, emotion: EmotionState) -> dict:
        """计算 PAD 向量"""
        from services.tts_emotion_engine import compute_pad_from_emotion, classify_mood
        p, a, d = compute_pad_from_emotion(emotion)
        mood = classify_mood(p, a, d)
        return {"pleasure": p, "arousal": a, "dominance": d, "mood": mood}
```

#### EventTool

```python
class EventTool(BaseTool):
    """事件管理工具"""

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

    def __init__(self):
        super().__init__("event")

    def get_available_events(self, beat_event_pool: list, used_events: set) -> list:
        """获取可用事件列表"""
        available = [e for e in beat_event_pool if e not in used_events]
        return available if available else beat_event_pool

    def select_event(self, available: list, chaos_factor: float = 0.08) -> str:
        """选择事件（带混沌因子）"""
        import random
        event = random.choice(available)
        if random.random() < chaos_factor:
            all_events = list(self.EVENT_TEMPLATES.keys())
            chaos = random.choice(all_events)
            if chaos != event:
                return chaos
        return event

    def build_event(self, event_type: str, scene: str, time: str,
                    weather: str, round_num: int) -> dict:
        """构建事件对象"""
        return {
            "type": event_type,
            "description": self.EVENT_TEMPLATES.get(event_type, "角色与玩家互动"),
            "scene": scene, "time": time, "weather": weather, "round": round_num,
        }

    def get_event_description(self, event_type: str) -> str:
        """获取事件描述"""
        return self.EVENT_TEMPLATES.get(event_type, "角色与玩家互动")
```

#### SceneTool

```python
class SceneTool(BaseTool):
    """场景管理工具"""

    WEATHER_CYCLE = ["clear", "clear", "clear", "cloudy", "cloudy", "rain", "clear"]

    def __init__(self, scenes_data: dict = None):
        super().__init__("scene")
        self.scenes_data = scenes_data or {}

    def advance_time(self, phase: str, elapsed: float) -> tuple:
        """推进时间"""
        import random
        increments = {"opening": 1.5, "rising": 2.0, "climax": 2.5, "resolution": 2.0}
        increment = increments.get(phase, 2.0) + random.uniform(-0.3, 0.3)
        new_elapsed = elapsed + increment

        if new_elapsed / 30.0 < 0.3:
            time_of_day = "morning"
        elif new_elapsed / 30.0 < 0.7:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"

        return new_elapsed, time_of_day

    def get_weather(self, round_num: int, weather_index: int) -> tuple:
        """获取天气"""
        if round_num % 3 == 0:
            weather_index = (weather_index + 1) % len(self.WEATHER_CYCLE)
        return self.WEATHER_CYCLE[weather_index], weather_index

    def should_change_scene(self, probability: float = 0.15) -> bool:
        """是否切换场景"""
        import random
        return random.random() < probability

    def get_available_scenes(self, current_scene: str) -> list:
        """获取可用场景"""
        return [s for s in self.scenes_data if s != current_scene]
```

---

## 四、大脑层设计（各 Agent）

### 4.1 DirectorAgent 大脑

```
┌─────────────────────────────────────────────────────────────┐
│ DirectorAgent Brain                                          │
├─────────────────────────────────────────────────────────────┤
│ 输入:                                                        │
│   - 短期记忆: narrative_state (phase, total_rounds)         │
│   - 长期记忆: game_events (事件数量)                         │
│   - 情绪状态: emotion (favorability, hostility)             │
│                                                              │
│ 推理逻辑:                                                    │
│   1. 规则: 根据 elapsed_minutes 返回当前节拍                 │
│   2. 规则: 检查结束条件（时间/轮次/情绪极化）               │
│   3. 规则: 从节拍事件池选择事件                              │
│                                                              │
│ 输出:                                                        │
│   - action: "continue" / "end_game"                         │
│   - selected_event: 事件类型                                 │
│   - phase: 叙事阶段                                          │
└─────────────────────────────────────────────────────────────┘
```

```python
class DirectorAgent(BaseAgent):
    """导演 Agent — 剧情走向 + 节奏控制 + 结局判断"""

    def __init__(self, text_gen=None, db_manager=None):
        super().__init__("director")
        self.tools = {
            "event": EventTool(),
            "scene": SceneTool(),
        }

    async def think(self, state: AgentState) -> Dict[str, Any]:
        """决策流程"""

        # 1. 节拍规划（规则）
        beat = self._plan_beat(state)
        state.current_beat = beat
        state.phase = beat.phase if beat else state.phase

        # 2. 结局判断（规则 + 情绪极化）
        if self._should_end(state):
            state.phase = SessionPhase.ENDING
            return {"action": "end_game", "reason": self._get_end_reason(state)}

        # 3. 事件选择（规则）
        event_tool = self.tools["event"]
        available = event_tool.get_available_events(
            beat.event_pool if beat else [],
            state.used_event_ids
        )
        selected_event = event_tool.select_event(available)

        return {
            "action": "continue",
            "beat": beat,
            "selected_event": selected_event,
            "phase": state.phase.value,
        }

    def _should_end(self, state: AgentState) -> bool:
        """结局判断（增强版）"""
        # 时间硬上限
        if state.world.elapsed_minutes >= 30.0:
            return True
        # 轮次硬上限
        if state.total_rounds >= 25:
            return True

        # 情绪极化触发（至少 8 轮后）
        if state.total_rounds >= 8:
            emotion = state.emotion
            # 美好结局提前
            if emotion.favorability >= 85 and emotion.trust >= 75 and emotion.happiness >= 70:
                return True
            # 悲剧结局提前
            if emotion.hostility >= 70:
                return True
            if emotion.favorability <= 15 and emotion.trust <= 20:
                return True

        return False

    def _get_end_reason(self, state: AgentState) -> str:
        """获取结局原因"""
        if state.world.elapsed_minutes >= 30.0:
            return "time_exceeded"
        if state.total_rounds >= 25:
            return "rounds_exceeded"
        if state.emotion.hostility >= 70:
            return "hostility_extreme"
        if state.emotion.favorability <= 15:
            return "favorability_collapse"
        return "emotion_extreme"
```

### 4.2 WorldSimulator 大脑

```
┌─────────────────────────────────────────────────────────────┐
│ WorldSimulator Brain                                         │
├─────────────────────────────────────────────────────────────┤
│ 输入:                                                        │
│   - 短期记忆: world_state (scene, time, weather, elapsed)   │
│   - 情绪状态: emotion (用于天气/场景联动)                    │
│   - 叙事阶段: phase                                          │
│                                                              │
│ 推理逻辑:                                                    │
│   1. 规则: 推进时间（按阶段不同步长）                        │
│   2. 规则: 更新时间段（morning/afternoon/evening）           │
│   3. 规则: 天气变化（每 3 轮）                               │
│   4. 规则: 场景切换（15% 概率）                              │
│                                                              │
│ 输出:                                                        │
│   - scene: 当前场景                                          │
│   - elapsed_minutes: 已过时间                                │
│   - weather: 天气                                            │
│   - scene_changed: 是否切换                                  │
└─────────────────────────────────────────────────────────────┘
```

```python
class WorldSimulator(BaseAgent):
    """世界模拟器 — 时间推进 + 天气 + 场景切换"""

    def __init__(self, scenes_data=None):
        super().__init__("world_simulator")
        self.tools = {"scene": SceneTool(scenes_data)}
        self._weather_index = 0

    async def think(self, state: AgentState) -> Dict[str, Any]:
        world = state.world
        scene_tool = self.tools["scene"]

        # 1. 推进时间
        phase = state.phase.value if state.phase else "rising"
        world.elapsed_minutes, world.current_time = scene_tool.advance_time(
            phase, world.elapsed_minutes
        )
        world.time_of_day_progress = world.elapsed_minutes / 30.0

        # 2. 天气变化
        world.weather, self._weather_index = scene_tool.get_weather(
            state.total_rounds, self._weather_index
        )

        # 3. 场景切换
        scene_changed = False
        if scene_tool.should_change_scene():
            available = scene_tool.get_available_scenes(world.current_scene)
            if available:
                import random
                world.current_scene = random.choice(available)
                scene_changed = True

        return {
            "elapsed_minutes": round(world.elapsed_minutes, 1),
            "current_time": world.current_time,
            "weather": world.weather,
            "scene": world.current_scene,
            "scene_changed": scene_changed,
        }
```

### 4.3 EmotionAgent 大脑

```
┌─────────────────────────────────────────────────────────────┐
│ EmotionAgent Brain                                           │
├─────────────────────────────────────────────────────────────┤
│ 输入:                                                        │
│   - 短期记忆: emotion_snapshot (12 维情绪)                   │
│   - 长期记忆: player_preferences (玩家偏好)                  │
│   - 玩家输入: last_player_input                              │
│   - 角色性格: character_personality                          │
│                                                              │
│ 推理逻辑:                                                    │
│   1. 规则: 情绪衰减（5 个维度）                              │
│   2. LLM: 分析玩家输入的情感倾向（可选，失败降级到关键词）  │
│   3. 规则: 应用性格修正                                      │
│   4. 规则: PAD 向量计算                                      │
│                                                              │
│ 输出:                                                        │
│   - state_changes: 情绪变化量                                │
│   - current_emotion: 当前情绪                                │
│   - pad: PAD 向量                                            │
└─────────────────────────────────────────────────────────────┘
```

```python
class EmotionAgent(BaseAgent):
    """情绪 Agent — 12 维情绪计算 + PAD 映射"""

    def __init__(self, llm_tool: LLMTool = None):
        super().__init__("emotion")
        self.tools = {
            "emotion": EmotionTool(),
            "llm": llm_tool,  # 可选，用于 LLM 情感分析
        }

    async def think(self, state: AgentState) -> Dict[str, Any]:
        emotion_tool = self.tools["emotion"]
        emotion = state.emotion

        # 1. 情绪衰减（规则）
        emotion_tool.apply_decay(emotion)

        # 2. 分析玩家输入
        player_text = state.last_player_input or ""
        if self.tools["llm"] and player_text:
            changes = await self._analyze_with_llm(player_text, state)
        else:
            changes = emotion_tool.analyze_keywords(player_text)

        # 3. 应用性格修正
        changes = self._apply_personality_modifiers(changes, state.character_personality)

        # 4. 应用变化
        emotion.apply_changes(changes)

        # 5. 计算 PAD
        pad = emotion_tool.calculate_pad(emotion)

        return {
            "state_changes": changes,
            "current_emotion": emotion.to_dict(),
            "pad": pad,
        }

    async def _analyze_with_llm(self, text: str, state: AgentState) -> dict:
        """LLM 情感分析（失败降级到关键词）"""
        try:
            personality = state.character_personality.get("keywords", [])
            prompt = f"""分析以下输入对角色情绪的影响。

角色性格：{'、'.join(personality) if personality else '普通'}
玩家输入：{text}

返回 JSON 格式的情绪变化（-10 到 +10）：
{{"favorability": N, "trust": N, "happiness": N, "stress": N, "confidence": N}}"""

            result = await self.tools["llm"].generate(
                prompt, max_tokens=100, temperature=0.7, call_type="dialogue"
            )

            import json
            # 提取 JSON
            if "{" in result:
                json_str = result[result.index("{"):result.rindex("}") + 1]
                changes = json.loads(json_str)
                return {k: max(-10.0, min(10.0, float(v))) for k, v in changes.items()}
        except Exception as e:
            self.logger.warning(f"LLM 情感分析失败，降级到关键词: {e}")

        # 降级
        return self.tools["emotion"].analyze_keywords(text)

    def _apply_personality_modifiers(self, changes: dict, personality: dict) -> dict:
        """性格修正"""
        keywords = personality.get("keywords", [])
        if not keywords:
            return changes

        # 简单修正：热情角色正面变化放大，高冷角色正面变化缩小
        modifiers = {
            "热情": {"favorability": 1.2, "happiness": 1.2},
            "高冷": {"favorability": 0.8, "happiness": 0.8},
            "温柔": {"favorability": 1.1, "trust": 1.1},
            "直率": {"favorability": 1.1, "stress": 1.1},
        }

        for keyword in keywords:
            if keyword in modifiers:
                for key, multiplier in modifiers[keyword].items():
                    if key in changes:
                        changes[key] = changes[key] * multiplier

        return {k: max(-10.0, min(10.0, v)) for k, v in changes.items()}
```

### 4.4 EventAgent 大脑

```
┌─────────────────────────────────────────────────────────────┐
│ EventAgent Brain                                             │
├─────────────────────────────────────────────────────────────┤
│ 输入:                                                        │
│   - 短期记忆: narrative_state.used_events (已用事件)         │
│   - 长期记忆: game_events (历史事件，避免重复)               │
│   - 当前节拍: current_beat (事件池)                          │
│   - 情绪状态: emotion (用于事件选择偏向)                     │
│                                                              │
│ 推理逻辑:                                                    │
│   1. 规则: 从节拍事件池排除已用事件                          │
│   2. 规则: 根据情绪状态偏向选择事件                          │
│   3. 规则: 混沌因子（8% 随机事件）                           │
│   4. LLM: 生成事件细节描述（可选）                           │
│                                                              │
│ 输出:                                                        │
│   - event: 事件对象                                          │
│   - event_type: 事件类型                                     │
└─────────────────────────────────────────────────────────────┘
```

```python
class EventAgent(BaseAgent):
    """事件 Agent — 事件池管理 + 情绪驱动选择"""

    def __init__(self, llm_tool: LLMTool = None):
        super().__init__("event")
        self.tools = {
            "event": EventTool(),
            "llm": llm_tool,
        }

    async def think(self, state: AgentState) -> Dict[str, Any]:
        event_tool = self.tools["event"]
        beat = state.current_beat

        if not beat:
            return {"event": None, "event_type": None}

        # 1. 获取可用事件
        available = event_tool.get_available_events(beat.event_pool, state.used_event_ids)

        # 2. 情绪驱动选择
        event_type = self._select_by_emotion(available, state.emotion)

        # 3. 混沌因子
        import random
        if random.random() < 0.08:
            all_events = list(event_tool.EVENT_TEMPLATES.keys())
            chaos = random.choice(all_events)
            if chaos != event_type:
                event_type = chaos

        # 4. 构建事件
        event = event_tool.build_event(
            event_type=event_type,
            scene=state.world.current_scene,
            time=state.world.current_time,
            weather=state.world.weather,
            round_num=state.total_rounds + 1,
        )

        # 5. 可选：LLM 生成事件细节
        if self.tools["llm"]:
            event["detail"] = await self._generate_detail(event, state)

        # 6. 记录已用事件
        state.used_event_ids.add(event_type)

        return {"event": event, "event_type": event_type}

    def _select_by_emotion(self, available: list, emotion: EmotionState) -> str:
        """根据情绪偏向选择事件"""
        import random

        # 高好感度偏向正面事件
        if emotion.favorability >= 70:
            positive = ["shared_activity", "personal_revelation", "help_moment", "promise"]
            weighted = [e for e in available if e in positive]
            if weighted:
                return random.choice(weighted)

        # 高敌意偏向冲突事件
        if emotion.hostility >= 40:
            negative = ["small_conflict", "major_conflict", "betrayal"]
            weighted = [e for e in available if e in negative]
            if weighted:
                return random.choice(weighted)

        return random.choice(available)

    async def _generate_detail(self, event: dict, state: AgentState) -> str:
        """LLM 生成事件细节"""
        try:
            prompt = f"""为以下事件生成 50 字的细节描述。

事件类型：{event['type']}
事件描述：{event['description']}
场景：{event['scene']}
角色：{state.character_name}
当前情绪：好感度{state.emotion.favorability:.0f}，信任度{state.emotion.trust:.0f}

请用一句话描述这个事件的具体情境。"""

            return await self.tools["llm"].generate(
                prompt, max_tokens=100, temperature=0.8, call_type="story"
            )
        except Exception:
            return event["description"]
```

### 4.5 DialogueAgent 大脑

```
┌─────────────────────────────────────────────────────────────┐
│ DialogueAgent Brain                                          │
├─────────────────────────────────────────────────────────────┤
│ 输入:                                                        │
│   - 短期记忆: working_memory (最近对话)                      │
│   - 长期记忆: event_summaries (事件摘要) + knowledge (知识)  │
│   - 情绪状态: emotion                                        │
│   - 当前事件: pending_event                                  │
│   - 角色信息: character_name, character_personality          │
│                                                              │
│ 推理逻辑:                                                    │
│   1. 构建 prompt（注入短期+长期记忆）                        │
│   2. LLM: 生成角色台词                                      │
│   3. 规则: 生成选项方向                                      │
│                                                              │
│ 输出:                                                        │
│   - character_dialogue: 角色台词                             │
│   - player_options: 玩家选项                                 │
└─────────────────────────────────────────────────────────────┘
```

```python
class DialogueAgent(BaseAgent):
    """对话 Agent — 台词生成 + 选项生成"""

    def __init__(self, text_gen=None):
        super().__init__("dialogue")
        self.tools = {"llm": LLMTool(text_gen)}

    async def think(self, state: AgentState) -> Dict[str, Any]:
        # 1. 构建 prompt
        prompt = self._build_prompt(state)

        # 2. 生成台词
        dialogue = await self._generate_dialogue(prompt)

        # 3. 生成选项
        options = self._generate_options(state, dialogue)

        return {"character_dialogue": dialogue, "player_options": options}

    async def think_stream(self, state: AgentState, on_token: Callable = None) -> Dict[str, Any]:
        """流式生成"""
        prompt = self._build_prompt(state)

        dialogue_parts = []
        async for chunk in self.tools["llm"].generate_stream(
            prompt, call_type="dialogue", on_token=on_token
        ):
            dialogue_parts.append(chunk)

        dialogue = "".join(dialogue_parts).strip()
        options = self._generate_options(state, dialogue)

        return {"character_dialogue": dialogue, "player_options": options}

    def _build_prompt(self, state: AgentState) -> str:
        """构建 prompt（注入短期+长期记忆）"""
        emotion = state.emotion
        world = state.world
        event = state.pending_event or {}

        parts = [
            f"你是{state.character_name}，性格：{'、'.join(state.character_personality.get('keywords', []))}。",
            f"场景：{world.current_scene}，时间：{world.current_time}，天气：{world.weather}。",
            f"当前事件：{event.get('description', '与玩家互动')}。",
            "",
            "你的情绪状态：",
            f"- 好感度：{emotion.favorability:.0f}/100",
            f"- 信任度：{emotion.trust:.0f}/100",
            f"- 快乐：{emotion.happiness:.0f}/100",
            f"- 压力：{emotion.stress:.0f}/100",
        ]

        # 注入长期记忆（事件摘要）
        if state.event_summaries:
            parts.append("")
            parts.append("之前的事件：")
            for i, summary in enumerate(state.event_summaries[-3:], 1):
                parts.append(f"{i}. {summary}")

        # 注入长期记忆（角色知识）
        if state.knowledge:
            parts.append("")
            parts.append("你对玩家的了解：")
            for k in state.knowledge[:3]:
                parts.append(f"- {k.get('content', '')}")

        # 注入短期记忆（最近对话）
        recent = state.dialogue_history[-6:]
        if recent:
            parts.append("")
            parts.append("最近对话：")
            for msg in recent:
                role = "玩家" if msg.get("role") == "player" else state.character_name
                parts.append(f"{role}: {msg.get('content', '')}")

        parts.append("")
        parts.append(f"请以{state.character_name}的口吻回复一句话（20-80字），符合当前情绪和剧情。")

        return "\n".join(parts)

    async def _generate_dialogue(self, prompt: str) -> str:
        """生成台词"""
        result = await self.tools["llm"].generate(
            prompt, max_tokens=100, temperature=0.9, call_type="dialogue"
        )
        return result if result else "..."

    def _generate_options(self, state: AgentState, dialogue: str) -> list:
        """生成选项（规则）"""
        return [
            {"id": 0, "text": "积极回应", "direction": "positive",
             "state_changes": {"favorability": 5, "trust": 3, "happiness": 3}},
            {"id": 1, "text": "中性回应", "direction": "neutral",
             "state_changes": {"favorability": 1, "trust": 1}},
            {"id": 2, "text": "消极回应", "direction": "negative",
             "state_changes": {"favorability": -3, "trust": -2, "stress": 2}},
        ]
```

### 4.6 ConsistencyAgent 大脑

```
┌─────────────────────────────────────────────────────────────┐
│ ConsistencyAgent Brain                                       │
├─────────────────────────────────────────────────────────────┤
│ 输入:                                                        │
│   - 短期记忆: emotion_snapshot (检查突变)                    │
│   - 短期记忆: working_memory (检查重复)                      │
│   - 输出: output_dialogue, output_emotion_changes           │
│                                                              │
│ 推理逻辑:                                                    │
│   1. 规则: 情绪突变检测（阈值 30）                           │
│   2. 规则: 对话内容校验（长度、重复性）                      │
│   3. 规则: 事件连续性检测                                    │
│                                                              │
│ 输出:                                                        │
│   - passed: 是否通过                                         │
│   - violations: 违规列表                                     │
│   - severity: 严重程度                                       │
└─────────────────────────────────────────────────────────────┘
```

```python
class ConsistencyAgent(BaseAgent):
    """一致性 Agent — 输出前校验"""

    MAX_EMOTION_DELTA = 30.0

    def __init__(self):
        super().__init__("consistency")

    async def think(self, state: AgentState) -> Dict[str, Any]:
        violations = []

        # 1. 情绪突变检测
        changes = state.output_emotion_changes
        for key, delta in changes.items():
            if abs(delta) > self.MAX_EMOTION_DELTA:
                violations.append(f"情绪[{key}]变化过大: {delta:.1f}")

        # 2. 对话内容校验
        dialogue = state.output_dialogue
        if dialogue:
            if state.character_name and state.character_name not in dialogue:
                # 不强制要求包含角色名，只警告
                pass
            if len(dialogue.strip()) < 5:
                violations.append("对话内容过短")
            if self._is_repetitive(dialogue):
                violations.append("对话内容重复度过高")

        # 3. 事件连续性检测
        if len(state.event_history) >= 2:
            last = state.event_history[-1]
            event_type = state.pending_event.get("type") if state.pending_event else None
            if event_type and last.get("type") == event_type:
                violations.append(f"连续重复事件: {event_type}")

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "severity": "error" if len(violations) >= 3 else ("warning" if violations else "ok"),
        }

    def _is_repetitive(self, text: str, threshold: float = 0.3) -> bool:
        """检测文本重复度"""
        if len(text) < 10:
            return False
        unique = len(set(text))
        return unique / len(text) < threshold
```

---

## 五、Orchestrator 集成

### 5.1 工具初始化

```python
class AgentOrchestrator:
    def __init__(self, text_gen, db_manager, redis_client, ...):
        # 工具层
        self.llm_tool = LLMTool(text_gen) if text_gen else None
        self.memory_tool = MemoryTool(
            RedisMemoryStore(redis_client),
            PgMemoryStore(db_manager)
        )
        self.emotion_tool = EmotionTool()
        self.event_tool = EventTool()
        self.scene_tool = SceneTool(scenes_data)

        # Agent 层（注入工具）
        self.director = DirectorAgent(text_gen, db_manager)
        self.emotion = EmotionAgent(llm_tool=self.llm_tool)
        self.world = WorldSimulator(scenes_data)
        self.event = EventAgent(llm_tool=self.llm_tool)
        self.consistency = ConsistencyAgent()
        self.dialogue = DialogueAgent(text_gen)
```

### 5.2 数据流（完整版）

```
玩家输入
  ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 1: MemoryTool.load_session(thread_id)                  │
│   → Redis: working_memory, emotion_snapshot, world_state    │
│   → PG: event_summaries, knowledge, preferences             │
│   → 填充到 AgentState                                        │
├─────────────────────────────────────────────────────────────┤
│ Step 2: DirectorAgent.think(state)                          │
│   → 使用: narrative_state, emotion                          │
│   → 输出: action, selected_event, phase                     │
├─────────────────────────────────────────────────────────────┤
│ Step 3: WorldSimulator.think(state)                         │
│   → 使用: world_state, phase                                │
│   → 输出: scene, elapsed_minutes, weather                   │
├─────────────────────────────────────────────────────────────┤
│ Step 4: EmotionAgent.think(state)                           │
│   → 使用: emotion_snapshot, last_player_input, personality  │
│   → 可选: LLMTool.analyze()                                 │
│   → 输出: state_changes, current_emotion, pad               │
├─────────────────────────────────────────────────────────────┤
│ Step 5: EventAgent.think(state)                             │
│   → 使用: used_events, current_beat, emotion                │
│   → 可选: LLMTool.generate() (事件细节)                     │
│   → 输出: event, event_type                                 │
├─────────────────────────────────────────────────────────────┤
│ Step 6: DialogueAgent.think(state)                          │
│   → 使用: working_memory, event_summaries, knowledge        │
│   → 使用: emotion, pending_event, character_info            │
│   → LLMTool.generate() → 台词                               │
│   → 输出: character_dialogue, player_options                 │
├─────────────────────────────────────────────────────────────┤
│ Step 7: TTSTool.generate() (异步)                           │
│   → 使用: character_dialogue, emotion                       │
│   → 输出: audio_url, audio_duration                         │
├─────────────────────────────────────────────────────────────┤
│ Step 8: ConsistencyAgent.think(state)                       │
│   → 使用: output_dialogue, output_emotion_changes           │
│   → 输出: passed, violations                                │
├─────────────────────────────────────────────────────────────┤
│ Step 9: MemoryTool.save_round(thread_id, ...)               │
│   → Redis: working_memory, emotion_snapshot, world_state    │
├─────────────────────────────────────────────────────────────┤
│ Step 10: [事件结束]                                          │
│   → MemoryTool.load_event_data() → Redis 全量               │
│   → LLMTool.compress() → 事件摘要                           │
│   → MemoryTool.save_event() → PG                            │
│   → MemoryTool.save_knowledge() → PG (可选)                 │
│   → Redis.clear_event_data()                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、优化效果预期

| Agent | 当前 | 优化后 | 提升 |
|-------|------|--------|------|
| DirectorAgent | 纯规则 | 规则 + 情绪极化结局 | 结局更自然 |
| WorldSimulator | 纯规则 | 规则（不变） | - |
| EmotionAgent | 20 词关键词 | 关键词 + LLM 分析 + 性格修正 | 情绪响应更准确 |
| EventAgent | 随机选择 | 情绪驱动 + LLM 细节 | 事件更贴合 |
| DialogueAgent | LLM 台词 + 硬编码选项 | LLM 台词 + 注入长期记忆 | 对话更丰富 |
| ConsistencyAgent | 3 条规则 | 规则（不变） | - |

### LLM 调用预算

| 操作 | 当前 | 优化后 |
|------|------|--------|
| 每轮 LLM 调用 | 1 次（台词） | 1-2 次（台词 + 可选情感分析） |
| 事件结束 | 0 次 | 1 次（压缩摘要） |
| 每局总调用 | ~15 次 | ~20-25 次 |
| 每局 Token | ~3000 | ~4000-5000 |
