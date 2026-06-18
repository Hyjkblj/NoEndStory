# Agent 记忆层升级设计

> Redis 短期记忆 + PostgreSQL 长期记忆，去掉 ChromaDB
> 更新日期: 2026-06-18

---

## 一、设计原则

```
1. 事件是记忆的最小单位
   → 一个事件 = 2-5 轮对话 = 一个 Redis key
   → 事件结束时压缩为摘要存入 PostgreSQL

2. 数据一致性优先
   → Redis 写入成功才算本轮完成
   → PostgreSQL 写入成功才算事件完成
   → 失败时有降级方案

3. 去掉 ChromaDB
   → 30 分钟游戏不需要语义检索
   → 用 PostgreSQL 时间排序查询替代
   → 未来需要时可加回

4. 每个 Agent 只访问自己需要的记忆
   → 不共享 MemoryManager
   → 通过 Orchestrator 协调读写
```

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      AgentOrchestrator                           │
│  负责: 协调各 Agent 的记忆读写，保证数据一致性                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Director │  │  World   │  │ Emotion  │  │  Event   │       │
│  │  Agent   │  │ Simulator│  │  Agent   │  │  Agent   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │             │
│       └──────────────┴──────────────┴──────────────┘             │
│                              │                                   │
│                    ┌─────────▼─────────┐                        │
│                    │    Orchestrator    │                        │
│                    │  统一记忆读写入口  │                        │
│                    └─────────┬─────────┘                        │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼                               ▼                  │
│  ┌───────────────────┐          ┌───────────────────┐          │
│  │   Redis           │          │   PostgreSQL       │          │
│  │   短期记忆        │          │   长期记忆         │          │
│  │                   │          │                    │          │
│  │  session:{tid}    │          │  game_events       │          │
│  │  ├─ working_mem   │──压缩──▶│  character_knowledge│          │
│  │  ├─ emotion       │          │  player_preferences│          │
│  │  ├─ world_state   │          │  dialogue_summaries│          │
│  │  └─ narrative     │          │                    │          │
│  └───────────────────┘          └───────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、Redis 短期记忆设计

### 3.1 Key 结构

```
Key:   noendstory:session:{thread_id}
Type:  Hash
TTL:   86400 秒（24 小时）

Hash Fields:
  working_memory    → JSON 字符串（最近 N 轮对话）
  emotion_snapshot  → JSON 字符串（12 维情绪快照）
  world_state       → JSON 字符串（场景/时间/天气）
  narrative_state   → JSON 字符串（阶段/轮次/已用事件）
  current_event     → JSON 字符串（当前事件信息）
  metadata          → JSON 字符串（character_id, 创建时间）
```

### 3.2 数据格式

```json
// working_memory
[
  {"role": "player", "content": "你好呀", "round": 1, "timestamp": 1718700000},
  {"role": "character", "content": "你好，今天天气真不错", "round": 1, "timestamp": 1718700001},
  {"role": "player", "content": "你最近怎么样？", "round": 2, "timestamp": 1718700060},
  {"role": "character", "content": "还不错，刚看完一本书", "round": 2, "timestamp": 1718700061}
]

// emotion_snapshot
{
  "favorability": 65.0,
  "trust": 55.0,
  "hostility": 10.0,
  "dependence": 50.0,
  "emotion": 60.0,
  "stress": 25.0,
  "anxiety": 15.0,
  "happiness": 60.0,
  "sadness": 15.0,
  "confidence": 55.0,
  "initiative": 50.0,
  "caution": 40.0
}

// world_state
{
  "scene": "library",
  "current_time": "afternoon",
  "weather": "clear",
  "elapsed_minutes": 8.5,
  "time_of_day_progress": 0.28
}

// narrative_state
{
  "phase": "rising",
  "total_rounds": 6,
  "round_count": 2,
  "current_event_type": "shared_activity",
  "current_beat_name": "关系建立",
  "used_events": ["first_meeting", "casual_chat"]
}

// current_event
{
  "type": "shared_activity",
  "description": "角色与玩家在图书馆一起看书",
  "scene": "library",
  "start_round": 5,
  "start_time": 1718700000
}

// metadata
{
  "character_id": 1,
  "character_name": "小明",
  "created_at": 1718700000,
  "last_updated": 1718700061
}
```

### 3.3 Redis 操作封装

```python
class RedisMemoryStore:
    """Redis 短期记忆存储"""

    KEY_PREFIX = "noendstory:session:"
    TTL = 86400  # 24 小时

    def __init__(self, redis_client):
        self.redis = redis_client

    def _key(self, thread_id: str) -> str:
        return f"{self.KEY_PREFIX}{thread_id}"

    # === 初始化 ===
    def init_session(self, thread_id: str, character_id: int, character_name: str):
        """初始化会话记忆"""
        key = self._key(thread_id)
        pipe = self.redis.pipeline()
        pipe.hset(key, "working_memory", "[]")
        pipe.hset(key, "emotion_snapshot", json.dumps(EmotionState().to_dict()))
        pipe.hset(key, "world_state", json.dumps(WorldState().__dict__))
        pipe.hset(key, "narrative_state", json.dumps({"phase": "opening", "total_rounds": 0}))
        pipe.hset(key, "current_event", "{}")
        pipe.hset(key, "metadata", json.dumps({
            "character_id": character_id,
            "character_name": character_name,
            "created_at": int(time.time()),
        }))
        pipe.expire(key, self.TTL)
        pipe.execute()

    # === 读取 ===
    def load_working_memory(self, thread_id: str) -> list:
        data = self.redis.hget(self._key(thread_id), "working_memory")
        return json.loads(data) if data else []

    def load_emotion_snapshot(self, thread_id: str) -> dict:
        data = self.redis.hget(self._key(thread_id), "emotion_snapshot")
        return json.loads(data) if data else {}

    def load_world_state(self, thread_id: str) -> dict:
        data = self.redis.hget(self._key(thread_id), "world_state")
        return json.loads(data) if data else {}

    def load_narrative_state(self, thread_id: str) -> dict:
        data = self.redis.hget(self._key(thread_id), "narrative_state")
        return json.loads(data) if data else {}

    def load_current_event(self, thread_id: str) -> dict:
        data = self.redis.hget(self._key(thread_id), "current_event")
        return json.loads(data) if data else {}

    def load_all(self, thread_id: str) -> dict:
        """一次性加载所有记忆（减少 Redis 往返）"""
        key = self._key(thread_id)
        data = self.redis.hgetall(key)
        return {
            "working_memory": json.loads(data.get("working_memory", "[]")),
            "emotion_snapshot": json.loads(data.get("emotion_snapshot", "{}")),
            "world_state": json.loads(data.get("world_state", "{}")),
            "narrative_state": json.loads(data.get("narrative_state", "{}")),
            "current_event": json.loads(data.get("current_event", "{}")),
            "metadata": json.loads(data.get("metadata", "{}")),
        }

    # === 写入（原子操作） ===
    def save_round(self, thread_id: str, player_input: str, character_dialogue: str,
                   emotion_snapshot: dict, world_state: dict, narrative_state: dict):
        """保存一轮对话（原子操作，保证一致性）"""
        key = self._key(thread_id)

        # 读取现有对话历史
        working_memory = self.load_working_memory(thread_id)
        round_num = len(working_memory) // 2 + 1
        timestamp = int(time.time())

        # 追加本轮对话
        working_memory.append({
            "role": "player", "content": player_input,
            "round": round_num, "timestamp": timestamp
        })
        working_memory.append({
            "role": "character", "content": character_dialogue,
            "round": round_num, "timestamp": timestamp
        })

        # 原子写入（pipeline 保证全部成功或全部失败）
        pipe = self.redis.pipeline()
        pipe.hset(key, "working_memory", json.dumps(working_memory))
        pipe.hset(key, "emotion_snapshot", json.dumps(emotion_snapshot))
        pipe.hset(key, "world_state", json.dumps(world_state))
        pipe.hset(key, "narrative_state", json.dumps(narrative_state))
        pipe.expire(key, self.TTL)  # 续期
        pipe.execute()

    def save_current_event(self, thread_id: str, event: dict):
        """保存当前事件信息"""
        self.redis.hset(self._key(thread_id), "current_event", json.dumps(event))

    # === 事件结束 ===
    def load_and_clear_event(self, thread_id: str) -> dict:
        """加载事件完整数据并标记为待清理（事件结束时调用）"""
        key = self._key(thread_id)
        data = self.load_all(thread_id)

        # 清空 working_memory（保留其他状态给下一个事件）
        pipe = self.redis.pipeline()
        pipe.hset(key, "working_memory", "[]")
        pipe.hset(key, "current_event", "{}")
        pipe.execute()

        return data

    # === 清理 ===
    def delete_session(self, thread_id: str):
        """删除会话记忆"""
        self.redis.delete(self._key(thread_id))
```

---

## 四、PostgreSQL 长期记忆设计

### 4.1 表结构

```sql
-- 游戏事件表（事件级压缩存储）
CREATE TABLE game_events (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL,
    thread_id VARCHAR(36) NOT NULL,

    -- 事件信息
    event_type VARCHAR(50) NOT NULL,
    event_summary TEXT NOT NULL,           -- LLM 压缩的摘要（100-200 字）
    scene VARCHAR(50),

    -- 情绪快照（事件结束时）
    emotion_start JSONB DEFAULT '{}',      -- 事件开始时的情绪
    emotion_end JSONB DEFAULT '{}',        -- 事件结束时的情绪
    emotion_delta JSONB DEFAULT '{}',      -- 情绪变化量

    -- 对话统计
    round_count INTEGER DEFAULT 0,         -- 事件内对话轮数
    player_choices JSONB DEFAULT '[]',     -- 玩家选择记录

    -- 世界状态
    world_state JSONB DEFAULT '{}',        -- 场景/时间/天气

    -- 元数据
    game_round_start INTEGER,              -- 事件开始时的总轮次
    game_round_end INTEGER,                -- 事件结束时的总轮次
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_game_events_character ON game_events(character_id);
CREATE INDEX idx_game_events_thread ON game_events(thread_id);
CREATE INDEX idx_game_events_created ON game_events(created_at);


-- 角色知识表（从事件中提取的长期知识）
CREATE TABLE character_knowledge (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL,

    -- 知识类型
    knowledge_type VARCHAR(50) NOT NULL,
    -- 'shared_experience'   共同经历
    -- 'player_preference'   玩家偏好
    -- 'emotional_moment'    情感时刻
    -- 'player_personality'  玩家性格推断

    -- 知识内容
    content TEXT NOT NULL,
    importance FLOAT DEFAULT 0.5,          -- 0-1 重要性评分

    -- 来源
    source_event_id INTEGER REFERENCES game_events(id),
    source_thread_id VARCHAR(36),

    -- 访问统计
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_character_knowledge_character ON character_knowledge(character_id);
CREATE INDEX idx_character_knowledge_type ON character_knowledge(knowledge_type);
CREATE INDEX idx_character_knowledge_importance ON character_knowledge(importance DESC);


-- 玩家偏好表（跨会话的玩家行为模式）
CREATE TABLE player_preferences (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL,

    -- 偏好维度
    preference_type VARCHAR(50) NOT NULL,
    -- 'response_tendency'   回应倾向（积极/消极/中性）
    -- 'topic_interest'      话题兴趣
    -- 'emotion_pattern'     情感模式

    -- 偏好值
    preference_value JSONB NOT NULL,
    sample_count INTEGER DEFAULT 1,
    confidence FLOAT DEFAULT 0.5,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(character_id, preference_type)
);

CREATE INDEX idx_player_preferences_character ON player_preferences(character_id);


-- 对话摘要表（长对话的压缩存储）
CREATE TABLE dialogue_summaries (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL,
    thread_id VARCHAR(36) NOT NULL,

    -- 摘要范围
    round_start INTEGER NOT NULL,
    round_end INTEGER NOT NULL,

    -- 摘要内容
    summary TEXT NOT NULL,
    key_points JSONB DEFAULT '[]',

    -- 情绪变化
    emotion_delta JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dialogue_summaries_character ON dialogue_summaries(character_id);
CREATE INDEX idx_dialogue_summaries_thread ON dialogue_summaries(thread_id);
```

### 4.2 PostgreSQL 操作封装

```python
class PgMemoryStore:
    """PostgreSQL 长期记忆存储"""

    def __init__(self, db_manager):
        self.db = db_manager

    # === 事件存储 ===
    def save_event(self, character_id: int, thread_id: str, event_data: dict):
        """保存事件（事件结束时调用）"""
        with self.db.get_session() as session:
            session.execute("""
                INSERT INTO game_events
                (character_id, thread_id, event_type, event_summary, scene,
                 emotion_start, emotion_end, emotion_delta,
                 round_count, player_choices, world_state,
                 game_round_start, game_round_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                character_id, thread_id,
                event_data['event_type'],
                event_data['event_summary'],
                event_data.get('scene'),
                json.dumps(event_data.get('emotion_start', {})),
                json.dumps(event_data.get('emotion_end', {})),
                json.dumps(event_data.get('emotion_delta', {})),
                event_data.get('round_count', 0),
                json.dumps(event_data.get('player_choices', [])),
                json.dumps(event_data.get('world_state', {})),
                event_data.get('game_round_start'),
                event_data.get('game_round_end'),
            ))

    def get_recent_events(self, character_id: int, n: int = 5) -> list:
        """获取最近 N 个事件"""
        with self.db.get_session() as session:
            results = session.execute("""
                SELECT id, event_type, event_summary, scene,
                       emotion_end, round_count, created_at
                FROM game_events
                WHERE character_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (character_id, n)).fetchall()
            return [dict(r) for r in results]

    def get_event_count(self, character_id: int, thread_id: str) -> int:
        """获取会话内的事件数量"""
        with self.db.get_session() as session:
            result = session.execute("""
                SELECT COUNT(*) FROM game_events
                WHERE character_id = %s AND thread_id = %s
            """, (character_id, thread_id)).fetchone()
            return result[0] if result else 0

    # === 知识存储 ===
    def save_knowledge(self, character_id: int, knowledge_type: str,
                       content: str, importance: float = 0.5,
                       source_event_id: int = None, source_thread_id: str = None):
        """保存角色知识"""
        with self.db.get_session() as session:
            session.execute("""
                INSERT INTO character_knowledge
                (character_id, knowledge_type, content, importance,
                 source_event_id, source_thread_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (character_id, knowledge_type, content, importance,
                  source_event_id, source_thread_id))

    def get_knowledge(self, character_id: int, knowledge_type: str = None,
                      limit: int = 10) -> list:
        """获取角色知识"""
        with self.db.get_session() as session:
            if knowledge_type:
                results = session.execute("""
                    SELECT * FROM character_knowledge
                    WHERE character_id = %s AND knowledge_type = %s
                    ORDER BY importance DESC, last_accessed DESC
                    LIMIT %s
                """, (character_id, knowledge_type, limit)).fetchall()
            else:
                results = session.execute("""
                    SELECT * FROM character_knowledge
                    WHERE character_id = %s
                    ORDER BY importance DESC, last_accessed DESC
                    LIMIT %s
                """, (character_id, limit)).fetchall()
            return [dict(r) for r in results]

    # === 偏好存储 ===
    def update_preference(self, character_id: int, preference_type: str,
                          preference_value: dict):
        """更新玩家偏好（upsert）"""
        with self.db.get_session() as session:
            session.execute("""
                INSERT INTO player_preferences
                (character_id, preference_type, preference_value, sample_count, confidence)
                VALUES (%s, %s, %s, 1, 0.5)
                ON CONFLICT (character_id, preference_type) DO UPDATE
                SET preference_value = %s,
                    sample_count = player_preferences.sample_count + 1,
                    confidence = LEAST(1.0, player_preferences.confidence + 0.1),
                    updated_at = NOW()
            """, (character_id, preference_type, json.dumps(preference_value),
                  json.dumps(preference_value)))

    def get_preferences(self, character_id: int) -> list:
        """获取玩家偏好"""
        with self.db.get_session() as session:
            results = session.execute("""
                SELECT preference_type, preference_value, confidence
                FROM player_preferences
                WHERE character_id = %s
                ORDER BY confidence DESC
            """, (character_id,)).fetchall()
            return [dict(r) for r in results]

    # === 摘要存储 ===
    def save_summary(self, character_id: int, thread_id: str,
                     round_start: int, round_end: int,
                     summary: str, key_points: list, emotion_delta: dict):
        """保存对话摘要"""
        with self.db.get_session() as session:
            session.execute("""
                INSERT INTO dialogue_summaries
                (character_id, thread_id, round_start, round_end,
                 summary, key_points, emotion_delta)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (character_id, thread_id, round_start, round_end,
                  summary, json.dumps(key_points), json.dumps(emotion_delta)))
```

---

## 五、各 Agent 记忆层设计

### 5.1 DirectorAgent

```
┌─────────────────────────────────────────────────────────────┐
│ DirectorAgent 记忆层                                         │
├─────────────────────────────────────────────────────────────┤
│ 短期记忆 (Redis)                                             │
│   读取: narrative_state (phase, total_rounds, used_events)  │
│   写入: 无（只读）                                           │
│                                                              │
│ 长期记忆 (PostgreSQL)                                        │
│   读取: game_events (获取事件数量，判断进度)                 │
│   写入: 无（只读）                                           │
│                                                              │
│ 数据一致性: 读取 Redis 失败 → 使用内存默认值                │
└─────────────────────────────────────────────────────────────┘
```

```python
class DirectorAgent:
    async def think(self, state: AgentState) -> Dict[str, Any]:
        # 从 state 读取（Orchestrator 已从 Redis 加载）
        beat = self._plan_beat(state)
        if self._should_end(state):
            return {"action": "end_game"}
        event = self._select_event(beat, state)
        return {"action": "continue", "selected_event": event}
```

### 5.2 WorldSimulator

```
┌─────────────────────────────────────────────────────────────┐
│ WorldSimulator 记忆层                                        │
├─────────────────────────────────────────────────────────────┤
│ 短期记忆 (Redis)                                             │
│   读取: world_state (scene, time, weather, elapsed)         │
│   写入: world_state (更新时间/天气/场景)                     │
│                                                              │
│ 长期记忆 (PostgreSQL)                                        │
│   读取: 无                                                   │
│   写入: 无                                                   │
│                                                              │
│ 数据一致性: 写入 Redis 失败 → 仅更新内存，下轮重试          │
└─────────────────────────────────────────────────────────────┘
```

```python
class WorldSimulator:
    async def think(self, state: AgentState) -> Dict[str, Any]:
        # 从 state 读取（Orchestrator 已从 Redis 加载）
        world = state.world
        # 更新世界状态
        world.elapsed_minutes += increment
        # 返回结果（Orchestrator 负责写回 Redis）
        return {"scene": world.current_scene, "elapsed_minutes": world.elapsed_minutes, ...}
```

### 5.3 EmotionAgent

```
┌─────────────────────────────────────────────────────────────┐
│ EmotionAgent 记忆层                                          │
├─────────────────────────────────────────────────────────────┤
│ 短期记忆 (Redis)                                             │
│   读取: emotion_snapshot (12 维情绪) + working_memory (历史) │
│   写入: emotion_snapshot (更新情绪)                          │
│                                                              │
│ 长期记忆 (PostgreSQL)                                        │
│   读取: player_preferences (玩家偏好，影响情绪计算)          │
│   写入: player_preferences (更新偏好)                        │
│                                                              │
│ 数据一致性:                                                   │
│   - 情绪更新 Redis 失败 → 仅更新内存，下轮重试              │
│   - 偏好更新 PG 失败 → 记录日志，不影响主流程               │
└─────────────────────────────────────────────────────────────┘
```

```python
class EmotionAgent:
    async def think(self, state: AgentState) -> Dict[str, Any]:
        # 从 state 读取（Orchestrator 已从 Redis 加载）
        emotion = state.emotion

        # 1. 自然衰减
        self._apply_decay(emotion)

        # 2. 分析玩家输入（可选：加载玩家偏好辅助判断）
        # preferences = pg_store.get_preferences(character_id)  # 1 次 PG 查询
        changes = self._analyze_player_impact(player_text, state)

        # 3. 应用变化
        emotion.apply_changes(changes)

        # 返回结果（Orchestrator 负责写回 Redis）
        return {"state_changes": changes, "current_emotion": emotion.to_dict()}
```

### 5.4 EventAgent

```
┌─────────────────────────────────────────────────────────────┐
│ EventAgent 记忆层                                            │
├─────────────────────────────────────────────────────────────┤
│ 短期记忆 (Redis)                                             │
│   读取: narrative_state.used_events (已用事件)               │
│   写入: narrative_state.used_events (追加新事件)             │
│                                                              │
│ 长期记忆 (PostgreSQL)                                        │
│   读取: game_events (获取历史事件，避免重复)                 │
│   写入: 无                                                   │
│                                                              │
│ 数据一致性: Redis 写入失败 → 仅更新内存，可能导致重复事件   │
└─────────────────────────────────────────────────────────────┘
```

```python
class EventAgent:
    async def think(self, state: AgentState) -> Dict[str, Any]:
        # 从 state 读取（Orchestrator 已从 Redis 加载）
        beat = state.current_beat
        used_events = state.used_event_ids

        # 选择事件（排除已用事件）
        available = [e for e in beat.event_pool if e not in used_events]
        event_type = random.choice(available)

        # 构建事件
        event = self._build_event(event_type, state)

        # 返回结果（Orchestrator 负责更新 used_events 并写回 Redis）
        return {"event": event, "event_type": event_type}
```

### 5.5 DialogueAgent

```
┌─────────────────────────────────────────────────────────────┐
│ DialogueAgent 记忆层                                         │
├─────────────────────────────────────────────────────────────┤
│ 短期记忆 (Redis)                                             │
│   读取: working_memory (最近 N 轮对话，注入 prompt)          │
│   读取: emotion_snapshot (情绪状态，调整语气)                │
│   读取: current_event (事件描述，上下文)                     │
│   写入: 无（只读）                                           │
│                                                              │
│ 长期记忆 (PostgreSQL)                                        │
│   读取: game_events (最近 3 个事件摘要，注入 prompt)         │
│   读取: character_knowledge (角色知识，丰富对话)             │
│   写入: 无                                                   │
│                                                              │
│ 数据一致性:                                                   │
│   - Redis 读取失败 → 使用 state 内存数据（降级）             │
│   - PG 读取失败 → 不注入历史摘要（降级）                     │
└─────────────────────────────────────────────────────────────┘
```

```python
class DialogueAgent:
    async def think(self, state: AgentState) -> Dict[str, Any]:
        # 从 state 读取（Orchestrator 已从 Redis/PG 加载）
        emotion = state.emotion
        event = state.pending_event
        recent_dialogue = state.dialogue_history[-6:]  # 最近 3 轮

        # 构建 prompt（注入短期 + 长期记忆）
        prompt = self._build_dialogue_prompt(
            state=state,
            recent_dialogue=recent_dialogue,      # 短期记忆
            event_summaries=state.event_summaries, # 长期记忆（Orchestrator 注入）
            character_knowledge=state.knowledge,   # 长期记忆（Orchestrator 注入）
        )

        # 生成台词
        dialogue = self._generate_dialogue(prompt)
        options = self._generate_options(state, dialogue)

        return {"character_dialogue": dialogue, "player_options": options}
```

### 5.6 ConsistencyAgent

```
┌─────────────────────────────────────────────────────────────┐
│ ConsistencyAgent 记忆层                                      │
├─────────────────────────────────────────────────────────────┤
│ 短期记忆 (Redis)                                             │
│   读取: emotion_snapshot (检查情绪突变)                      │
│   读取: working_memory (检查对话重复)                        │
│   写入: 无（只读）                                           │
│                                                              │
│ 长期记忆 (PostgreSQL)                                        │
│   读取: game_events (检查事件连续性)                         │
│   写入: 无                                                   │
│                                                              │
│ 数据一致性: 读取失败 → 跳过对应检查（降级）                  │
└─────────────────────────────────────────────────────────────┘
```

```python
class ConsistencyAgent:
    async def think(self, state: AgentState) -> Dict[str, Any]:
        violations = []

        # 1. 情绪突变检测（从 state 读取）
        changes = state.output_emotion_changes
        for key, delta in changes.items():
            if abs(delta) > 30.0:
                violations.append(f"情绪[{key}]变化过大: {delta:.1f}")

        # 2. 对话内容校验（从 state 读取）
        dialogue = state.output_dialogue
        if len(dialogue.strip()) < 5:
            violations.append("对话内容过短")

        # 3. 事件连续性检测（从 state 读取）
        if len(state.event_history) >= 2:
            last = state.event_history[-1]
            if state.pending_event.get("type") == last.get("type"):
                violations.append(f"连续重复事件")

        return {"passed": len(violations) == 0, "violations": violations}
```

---

## 六、Orchestrator 记忆协调

### 6.1 数据流（每轮）

```
玩家输入
  ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 从 Redis 加载所有记忆                                │
│   redis_store.load_all(thread_id)                           │
│   → working_memory, emotion_snapshot, world_state, ...      │
│   → 填充到 AgentState                                        │
├─────────────────────────────────────────────────────────────┤
│ Step 2: 从 PostgreSQL 加载长期记忆（首次或定期）             │
│   pg_store.get_recent_events(character_id, n=3)             │
│   → 填充到 state.event_summaries                             │
│   pg_store.get_knowledge(character_id)                      │
│   → 填充到 state.knowledge                                   │
├─────────────────────────────────────────────────────────────┤
│ Step 3: Agent 流水线处理                                     │
│   Director → World → Emotion → Event → Dialogue → TTS      │
│   → Consistency                                              │
├─────────────────────────────────────────────────────────────┤
│ Step 4: 写回 Redis（原子操作）                               │
│   redis_store.save_round(                                   │
│       thread_id, player_input, character_dialogue,          │
│       emotion_snapshot, world_state, narrative_state        │
│   )                                                          │
├─────────────────────────────────────────────────────────────┤
│ Step 5: 检查事件是否结束                                     │
│   [不结束] → 等待下一轮                                      │
│   [结束] ↓                                                   │
├─────────────────────────────────────────────────────────────┤
│ Step 6: 事件结束处理                                         │
│   6a. 从 Redis 加载完整事件数据                              │
│   6b. LLM 压缩为事件摘要                                    │
│   6c. LLM 提取角色知识（可选）                               │
│   6d. 存入 PostgreSQL                                        │
│   6e. 清理 Redis 事件数据                                    │
│   6f. 更新 state.event_summaries                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Orchestrator 实现

```python
class AgentOrchestrator:
    def __init__(self, text_gen, db_manager, redis_client, ...):
        self.text_gen = text_gen
        self.redis_store = RedisMemoryStore(redis_client)
        self.pg_store = PgMemoryStore(db_manager)

    async def process_input(self, user_input: str, thread_id: str) -> Dict:
        state = self._states[thread_id]

        # Step 1: 从 Redis 加载记忆
        redis_data = self.redis_store.load_all(thread_id)
        state.dialogue_history = redis_data["working_memory"]
        state.emotion = EmotionState.from_dict(redis_data["emotion_snapshot"])
        state.world = WorldState.from_dict(redis_data["world_state"])
        # ... 加载其他状态

        # Step 2: 从 PostgreSQL 加载长期记忆（首次加载）
        if not state.event_summaries:
            recent_events = self.pg_store.get_recent_events(state.character_id, n=3)
            state.event_summaries = [e["event_summary"] for e in recent_events]
            state.knowledge = self.pg_store.get_knowledge(state.character_id)

        # Step 3: 记录玩家输入
        state.last_player_input = user_input
        state.advance_round()
        state.add_to_history("player", user_input)

        # Step 4: Agent 流水线
        director_result = await self.director.think(state)
        if director_result.get("action") == "end_game":
            return await self._build_ending_output(state)

        world_result = await self.world.think(state)
        emotion_result = await self.emotion.think(state)
        event_result = await self.event.think(state)
        dialogue_result = await self.dialogue.think(state)
        consistency_result = await self.consistency.think(state)

        # Step 5: 写回 Redis
        character_dialogue = dialogue_result["character_dialogue"]
        self.redis_store.save_round(
            thread_id=thread_id,
            player_input=user_input,
            character_dialogue=character_dialogue,
            emotion_snapshot=state.emotion.to_dict(),
            world_state=state.world.__dict__,
            narrative_state={
                "phase": state.phase.value,
                "total_rounds": state.total_rounds,
                "used_events": list(state.used_event_ids),
            }
        )

        # Step 6: 检查事件是否结束
        if self._is_event_ended(state):
            await self._handle_event_end(state, thread_id)

        return self._build_output(state)

    async def _handle_event_end(self, state: AgentState, thread_id: str):
        """事件结束处理"""
        # 6a. 从 Redis 加载完整事件数据
        event_data = self.redis_store.load_and_clear_event(thread_id)

        # 6b. LLM 压缩为事件摘要
        summary = await self._compress_event(event_data)

        # 6c. 存入 PostgreSQL
        self.pg_store.save_event(
            character_id=state.character_id,
            thread_id=thread_id,
            event_data={
                "event_type": state.pending_event.get("type"),
                "event_summary": summary,
                "scene": state.world.current_scene,
                "emotion_start": event_data.get("emotion_start", {}),
                "emotion_end": state.emotion.to_dict(),
                "emotion_delta": state.output_emotion_changes,
                "round_count": len(event_data["working_memory"]) // 2,
                "player_choices": self._extract_choices(event_data["working_memory"]),
                "world_state": state.world.__dict__,
                "game_round_start": state.total_rounds - len(event_data["working_memory"]) // 2,
                "game_round_end": state.total_rounds,
            }
        )

        # 6d. 更新 state.event_summaries
        state.event_summaries.append(summary)
```

---

## 七、数据一致性保证

### 7.1 一致性级别

| 操作 | 一致性级别 | 失败处理 |
|------|-----------|---------|
| Redis 写入（每轮） | 强一致（pipeline 原子） | 仅更新内存，下轮重试 |
| PG 写入（事件结束） | 强一致（事务） | 记录日志，不影响主流程 |
| Redis → PG 压缩 | 最终一致 | 重试 3 次，失败记录日志 |
| PG 读取（初始化） | 强一致 | 使用空列表降级 |

### 7.2 失败场景处理

```
场景 1: Redis 写入失败
  影响: 本轮对话未持久化
  处理: 仅更新内存 state，下轮重试
  恢复: 下轮写入时会包含本轮数据（working_memory 是全量写入）

场景 2: PG 写入失败（事件结束时）
  影响: 事件摘要未保存
  处理: 重试 3 次，失败记录日志
  恢复: Redis 中的事件数据已清理，但 state 中仍有摘要

场景 3: Redis 读取失败
  影响: 无法加载历史对话
  处理: 使用空数据降级（相当于新会话）
  恢复: 下轮写入时会覆盖

场景 4: PG 读取失败（初始化时）
  影响: 无法加载历史事件摘要
  处理: 使用空列表降级
  恢复: 不影响当前会话

场景 5: Redis 和 PG 同时失败
  影响: 记忆完全丢失
  处理: 使用内存 state 继续（降级到当前系统行为）
  恢复: 服务重启后重新初始化
```

### 7.3 数据校验

```python
def validate_redis_data(data: dict) -> bool:
    """校验 Redis 数据完整性"""
    required_keys = ["working_memory", "emotion_snapshot", "world_state", "narrative_state"]
    return all(key in data for key in required_keys)

def validate_emotion_snapshot(snapshot: dict) -> bool:
    """校验情绪快照完整性"""
    required_fields = ["favorability", "trust", "hostility", "happiness", "sadness"]
    return all(field in snapshot for field in required_fields)

def validate_event_data(event_data: dict) -> bool:
    """校验事件数据完整性"""
    return (
        "event_type" in event_data and
        "event_summary" in event_data and
        len(event_data.get("event_summary", "")) > 10
    )
```

---

## 八、性能预算

| 操作 | 延迟 | 频率 | 说明 |
|------|------|------|------|
| Redis 读取（load_all） | <1ms | 每轮 1 次 | HGETALL 单 key |
| Redis 写入（save_round） | <1ms | 每轮 1 次 | pipeline 原子写入 |
| PG 读取（get_recent_events） | 2-5ms | 初始化 1 次 | 索引命中 |
| PG 读取（get_knowledge） | 2-5ms | 初始化 1 次 | 索引命中 |
| PG 写入（save_event） | 5-10ms | 事件结束 1 次 | 事务写入 |
| LLM 压缩（compress_event） | 1-3s | 事件结束 1 次 | 100-200 tokens |
| **每轮总延迟增加** | **<2ms** | | Redis 读写 |
| **事件结束延迟增加** | **1-3s** | | LLM 压缩 |

---

## 九、与当前系统的对比

| 维度 | 当前系统 | 新方案 |
|------|---------|--------|
| 短期存储 | 内存 Python 列表 | Redis Hash |
| 长期存储 | ChromaDB 向量库 | PostgreSQL |
| 压缩 | ❌ 无 | ✅ 事件结束时 LLM 压缩 |
| 持久化 | ❌ 服务重启丢失 | ✅ Redis + PG 双持久化 |
| 数据一致性 | ⚠️ 无保证 | ✅ Redis pipeline + PG 事务 |
| 跨事件上下文 | ⚠️ 全量历史 | ✅ 加载最近 3 个事件摘要 |
| 架构复杂度 | 内存 + PG + ChromaDB | Redis + PG |
| 每轮延迟 | <1ms | <2ms |
| 事件结束延迟 | 0 | 1-3s（LLM 压缩） |
