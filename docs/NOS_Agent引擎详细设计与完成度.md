# NOS Agent 引擎详细设计与完成度分析

> 6 个专业 Agent 的三层架构（大脑/工具/记忆）设计、当前状态与优化方向
> 更新日期: 2026-06-18

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     AgentOrchestrator                            │
│  流水线：Director → World → Emotion → Event → Dialogue → TTS    │
│  → Consistency → Output                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Director │  │  World   │  │ Emotion  │  │  Event   │       │
│  │  Agent   │  │ Simulator│  │  Agent   │  │  Agent   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                 │
│  ┌──────────┐  ┌──────────┐                                    │
│  │ Dialogue │  │Consisten-│                                    │
│  │  Agent   │  │cy Agent  │                                    │
│  └──────────┘  └──────────┘                                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  共享状态: AgentState (EmotionState + WorldState + History)      │
│  外部服务: ImageService + TTSService                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、三层架构定义

每个 Agent 由三层组成：

| 层级 | 职责 | 说明 |
|------|------|------|
| **大脑 (Brain)** | 推理与决策 | LLM 调用、规则引擎、算法逻辑 |
| **工具 (Tools)** | 外部交互 | 数据库查询、向量检索、API 调用、文件操作 |
| **记忆 (Memory)** | 状态与历史 | 即时状态、对话历史、事件记录、情绪快照 |

---

## 三、各 Agent 详细设计

### 3.1 DirectorAgent（导演 Agent）

**职责**: 控制剧情走向、节奏、结局判断

#### 三层设计

```
┌─────────────────────────────────────────────────────────────┐
│ DirectorAgent                                                │
├─────────────────────────────────────────────────────────────┤
│ 大脑 (Brain)                                                 │
│   ├─ 叙事节拍规划: 根据 elapsed_minutes 返回当前节拍          │
│   ├─ 结局判断: 时间≥30min 或 轮次≥25 → 结束                  │
│   ├─ 事件选择: 从节拍事件池加权采样                           │
│   └─ 候选评分: 3 候选方案的情绪/一致性/节拍匹配评分           │
│                                                              │
│ 工具 (Tools)                                                 │
│   ├─ narrative_beats.get_current_beat() — 节拍表查询         │
│   └─ [缺失] 情绪状态查询（应接入 EmotionAgent 结果）         │
│                                                              │
│ 记忆 (Memory)                                                │
│   ├─ state.world.elapsed_minutes — 游戏内时间                │
│   ├─ state.total_rounds — 总轮次                             │
│   ├─ state.used_event_ids — 已使用事件集合                   │
│   └─ state.current_beat — 当前节拍                           │
└─────────────────────────────────────────────────────────────┘
```

#### 三层实现细节

**大脑 (Brain) — 决策逻辑**

```python
# 文件: game/agents/director_agent.py
# 入口: async def think(self, state: AgentState) -> Dict[str, Any]

# 1. 节拍规划（纯规则）
beat = self._plan_beat(state)
# → 调用 narrative_beats.get_current_beat(elapsed_minutes)
# → 返回 NarrativeBeat 对象（含 phase, event_pool, emotion_target）

# 2. 结局判断（纯规则，无 LLM）
if self._should_end(state):
    # 条件: elapsed >= 30.0 OR total_rounds >= 25
    return {"action": "end_game", "reason": "game_time_exceeded"}

# 3. 事件选择（随机采样）
event = self._select_event(beat, state)
# → 从 beat.event_pool 中排除 state.used_event_ids
# → random.choice(available)

# 4. 候选评分（规则引擎）
evaluate_candidates(candidates, state)
# → 评分维度: 情绪影响分 + 新颖性分
# → 返回得分最高的候选
```

**工具 (Tools) — 外部能力**

```python
# 当前已实现:
narrative_beats.get_current_beat(elapsed_minutes)  # 节拍表查询

# 当前缺失:
# - 无 LLM 调用（所有决策都是规则）
# - 无向量检索（不查询历史相似事件）
# - 无情绪状态感知（不读取 EmotionAgent 结果）
```

**记忆 (Memory) — 状态访问**

```python
# 通过 AgentState 访问:
state.world.elapsed_minutes    # 游戏内已过时间（分钟）
state.total_rounds             # 总对话轮次
state.used_event_ids           # 已使用过的事件 ID 集合（set）
state.current_beat             # 当前 NarrativeBeat 对象
state.phase                    # 当前 SessionPhase 枚举

# 写入:
state.current_beat = beat      # 更新当前节拍
state.phase = beat.phase       # 更新游戏阶段
```

#### 当前状态: ⭐⭐⭐⭐ 85%

| 功能 | 状态 | 说明 |
|------|------|------|
| 叙事节拍表 | ✅ 完成 | 4 幕 30 分钟，每幕有事件池和情感目标 |
| 结局判断 | ⚠️ 部分完成 | 只看时间/轮次，不看情绪极化 |
| 事件选择 | ✅ 完成 | 加权采样 + 未使用事件优先 |
| 候选评分 | ⚠️ 部分完成 | 逻辑简单，只有 2 个评分维度 |
| **LLM 推理** | ❌ 未实现 | 所有决策都是规则，无 LLM 参与 |
| **情绪感知** | ❌ 未实现 | 不感知当前情绪状态 |

#### 差距与优化

```
差距 1: 结局判断不看情绪
  当前: elapsed >= 30 OR rounds >= 25
  应该: 上述条件 + 情绪极化触发（fav≥85 或 hostility≥70）
  改动: _should_end() 增加情绪检查

差距 2: 无 LLM 推理
  当前: 纯规则（时间阈值 + 随机采样）
  应该: LLM 分析当前剧情走向，动态调整节拍
  改动: think() 中增加可选的 LLM 调用

差距 3: 候选评分太简单
  当前: 只看情绪影响和新颖性
  应该: 增加剧情连贯性、角色性格匹配、玩家偏好学习
  改动: evaluate_candidates() 扩展评分维度
```

---

### 3.2 WorldSimulator（世界模拟器）

**职责**: 推进游戏内时间、管理天气、触发场景切换

#### 三层设计

```
┌─────────────────────────────────────────────────────────────┐
│ WorldSimulator                                               │
├─────────────────────────────────────────────────────────────┤
│ 大脑 (Brain)                                                 │
│   ├─ 时间推进: 根据阶段不同步长（1.5~2.5 min/轮）            │
│   ├─ 时间段更新: morning → afternoon → evening               │
│   ├─ 天气循环: 每 3 轮变化一次                               │
│   └─ 场景切换: 15% 概率随机切换                              │
│                                                              │
│ 工具 (Tools)                                                 │
│   ├─ [缺失] 场景数据查询（应接入 SCENES 配置）               │
│   └─ [缺失] 天气 API（应根据剧情动态调整）                   │
│                                                              │
│ 记忆 (Memory)                                                │
│   ├─ state.world.elapsed_minutes — 累计时间                  │
│   ├─ state.world.current_time — 当前时间段                   │
│   ├─ state.world.weather — 当前天气                          │
│   └─ state.world.current_scene — 当前场景                    │
└─────────────────────────────────────────────────────────────┘
```

#### 三层实现细节

**大脑 (Brain) — 决策逻辑**

```python
# 文件: game/agents/world_simulator.py
# 入口: async def think(self, state: AgentState) -> Dict[str, Any]

# 1. 时间推进（纯规则）
phase = state.phase.value  # "opening"/"rising"/"climax"/"resolution"
increment = PHASE_TIME_INCREMENT.get(phase, 2.0)  # 各阶段不同步长
world.elapsed_minutes += increment + random.uniform(-0.3, 0.3)  # 带随机抖动

# 2. 时间段更新（阈值判断）
if progress < 0.3: world.current_time = "morning"
elif progress < 0.7: world.current_time = "afternoon"
else: world.current_time = "evening"

# 3. 天气循环（固定模式）
WEATHER_CYCLE = ["clear", "clear", "clear", "cloudy", "cloudy", "rain", "clear"]
if state.total_rounds % 3 == 0:
    self._weather_index = (self._weather_index + 1) % len(WEATHER_CYCLE)

# 4. 场景切换（随机概率）
if random.random() < 0.15:  # 15% 概率
    available = [s for s in self.scenes_data if s != world.current_scene]
    world.current_scene = random.choice(available)
```

**工具 (Tools) — 外部能力**

```python
# 当前已实现:
self.scenes_data  # 场景数据字典（构造时注入）

# 当前缺失:
# - 无场景数据查询（场景列表硬编码在 scenes_data 中）
# - 无天气 API（天气变化是固定循环）
# - 无 LLM 调用（不根据剧情调整时间/天气/场景）
```

**记忆 (Memory) — 状态访问**

```python
# 通过 state.world 访问（WorldState 对象）:
state.world.elapsed_minutes       # 游戏内已过时间（float，分钟）
state.world.current_time          # "morning"/"afternoon"/"evening"
state.world.weather               # "clear"/"cloudy"/"rain"
state.world.current_scene         # 场景 ID（如 "classroom"）
state.world.time_of_day_progress  # 日夜进度（0.0~1.0）

# 写入:
world.elapsed_minutes += increment  # 更新时间
world.current_time = "afternoon"    # 更新时间段
world.weather = "rain"              # 更新天气
world.current_scene = "library"     # 更新场景
state.output_scene = scene          # 设置输出场景
```

#### 当前状态: ⭐⭐⭐⭐⭐ 95%

| 功能 | 状态 | 说明 |
|------|------|------|
| 时间推进 | ✅ 完成 | 按阶段不同步长，带随机抖动 |
| 时间段更新 | ✅ 完成 | 3 段式（morning/afternoon/evening） |
| 天气循环 | ✅ 完成 | 7 种天气状态循环 |
| 场景切换 | ✅ 完成 | 15% 概率，排除当前场景 |
| **剧情驱动场景** | ❌ 未实现 | 场景切换是纯随机，不考虑剧情 |
| **天气与情绪联动** | ❌ 未实现 | 天气变化与剧情/情绪无关 |

#### 差距与优化

```
差距 1: 场景切换是纯随机
  当前: 15% 概率从可用场景中随机选
  应该: 根据剧情阶段和情绪状态选择合适场景
        （悲伤剧情→雨天，开心剧情→阳光）
  改动: _select_scene() 增加剧情/情绪权重

差距 2: 天气与剧情无关
  当前: 固定循环 clear→cloudy→rain→clear
  应该: 根据情绪基调调整天气
        （高潮→暴风雨，收束→晴朗）
  改动: 天气选择增加情绪权重
```

---

### 3.3 EmotionAgent（情绪 Agent）

**职责**: 计算 12 维情绪变化、维护 PAD 空间、情绪衰减

#### 三层设计

```
┌─────────────────────────────────────────────────────────────┐
│ EmotionAgent                                                 │
├─────────────────────────────────────────────────────────────┤
│ 大脑 (Brain)                                                 │
│   ├─ 情绪衰减: stress×0.85, anxiety×0.90, happiness×0.97    │
│   ├─ 关键词匹配: 20+ 个正面/负面/支持性关键词                │
│   ├─ PAD 向量计算: pleasure, arousal, dominance              │
│   └─ [缺失] LLM 情感分析                                    │
│                                                              │
│ 工具 (Tools)                                                 │
│   ├─ [缺失] LLM 调用（分析玩家输入的情感倾向）              │
│   └─ [缺失] 向量检索（相似情感场景参考）                    │
│                                                              │
│ 记忆 (Memory)                                                │
│   ├─ state.emotion — 12 维情绪状态                          │
│   ├─ state.last_player_input — 玩家最后输入                 │
│   └─ [缺失] 情绪变化历史（用于趋势分析）                    │
└─────────────────────────────────────────────────────────────┘
```

#### 三层实现细节

**大脑 (Brain) — 决策逻辑**

```python
# 文件: game/agents/emotion_agent.py
# 入口: async def think(self, state: AgentState) -> Dict[str, Any]

# 1. 情绪衰减（纯规则）
DECAY_RATES = {
    "stress": 0.15,      # 压力每轮衰减 15%
    "anxiety": 0.10,     # 焦虑每轮衰减 10%
    "emotion": 0.05,     # 整体情绪每轮衰减 5%
    "happiness": 0.03,   # 快乐每轮衰减 3%
    "sadness": 0.08,     # 悲伤每轮衰减 8%
}
for key, rate in DECAY_RATES.items():
    current = getattr(emotion, key)
    setattr(emotion, key, max(0.0, current * (1 - rate)))

# 2. 关键词匹配（硬编码规则，无 LLM）
player_text = state.last_player_input.lower()
positive = {"谢谢", "喜欢你", "好的", "可以", "好", "真棒", ...}  # 20+ 词
negative = {"讨厌", "不喜欢", "不行", "不好", "滚", "烦", ...}
supportive = {"我相信你", "你可以", "没问题", "加油", ...}

for word in positive:
    if word in text:
        changes["favorability"] += 2.0
        changes["happiness"] += 1.5
# ... negative 和 supportive 类似

# 3. 变化幅度限制
for k in changes:
    changes[k] = max(-10.0, min(10.0, changes[k]))  # 硬编码 ±10

# 4. 应用变化
emotion.apply_changes(changes)  # 自动 clamp 到 0-100

# 5. PAD 向量计算
pad = emotion.pad_vector()
# pleasure = (happiness - sadness + favorability/2) / 2 + 50
# arousal = (emotion + stress + anxiety) / 3
# dominance = (confidence + initiative - caution) / 2 + 50
```

**工具 (Tools) — 外部能力**

```python
# 当前已实现: 无（所有计算都是纯规则）

# 当前缺失:
# - 无 LLM 调用（应分析玩家输入的情感倾向和强度）
# - 无向量检索（应查询历史相似情感场景）
# - 无外部知识库（应参考角色性格调整反应）
```

**记忆 (Memory) — 状态访问**

```python
# 读取:
state.emotion                  # EmotionState 对象（12 维）
state.last_player_input        # 玩家最后输入的文本
state.character_personality    # 角色性格关键词（未使用）

# 写入:
emotion.apply_changes(changes) # 更新 12 维情绪值
state.output_emotion_changes   # 记录本次变化量

# EmotionState 结构:
@dataclass
class EmotionState:
    favorability: float = 50.0  # 好感度
    trust: float = 50.0         # 信任度
    hostility: float = 0.0      # 敌意值
    dependence: float = 50.0    # 依赖度
    emotion: float = 50.0       # 整体情绪
    stress: float = 0.0         # 压力
    anxiety: float = 0.0        # 焦虑
    happiness: float = 50.0     # 快乐
    sadness: float = 0.0        # 悲伤
    confidence: float = 50.0    # 自信
    initiative: float = 50.0    # 主动性
    caution: float = 0.0        # 谨慎度
```

#### 当前状态: ⭐⭐⭐ 60%

| 功能 | 状态 | 说明 |
|------|------|------|
| 情绪衰减 | ✅ 完成 | 5 个维度有衰减率 |
| 关键词匹配 | ⚠️ 简陋 | 只有 20+ 个关键词，覆盖率低 |
| PAD 向量 | ✅ 完成 | 已接入 ALMA 论文的 PAD 空间 |
| 变化幅度限制 | ⚠️ 过于保守 | 单次 ±10，30 分钟可能到不了极端值 |
| **LLM 情感分析** | ❌ 未实现 | 应该用 LLM 分析玩家输入的情感倾向 |
| **上下文感知** | ❌ 未实现 | 不考虑对话历史的累积效应 |
| **性格修正** | ❌ 未实现 | 不根据角色性格调整情绪响应 |
| **情绪趋势** | ❌ 未实现 | 不追踪情绪变化方向 |

#### 差距与优化（最高优先级）

```
差距 1: 关键词匹配太简单（最大问题）
  当前: 20+ 个硬编码关键词 → 每次变化 ±2~3
  问题: "我觉得你今天有点不对劲" → 无匹配 → 无变化
  应该: LLM 分析玩家输入 → 返回情感倾向和强度
  改动:
    1. _analyze_player_impact() 增加 LLM 调用
    2. Prompt: "分析以下输入的情感倾向，返回 JSON {favorability:+5, trust:-3, ...}"
    3. 关键词匹配作为 LLM 的降级方案

差距 2: 变化幅度太保守
  当前: 单次变化 ±10，clamp 到 ±10
  问题: 30 分钟游戏，15 轮输入，最大变化 15×10=150（但 fav 范围 0-100）
  应该: 根据输入强度动态调整（轻微→±3，强烈→±15）
  改动: 去掉硬编码 ±10 限制，改为 LLM 返回的强度值

差距 3: 不考虑角色性格
  当前: 所有角色对同一输入的反应相同
  应该: 高冷角色对"我喜欢你"的反应 vs 热情角色的反应
  改动: 在 prompt 中注入角色性格关键词

差距 4: 不考虑上下文
  当前: 只看当前输入，不看历史
  应该: 连续 3 次正面输入 → 情绪加速上升
  改动: 将最近 3 轮对话历史传入 LLM prompt
```

---

### 3.4 EventAgent（事件 Agent）

**职责**: 管理事件池、加权采样、注入随机性

#### 三层设计

```
┌─────────────────────────────────────────────────────────────┐
│ EventAgent                                                   │
├─────────────────────────────────────────────────────────────┤
│ 大脑 (Brain)                                                 │
│   ├─ 事件选择: 从节拍事件池加权采样                          │
│   ├─ 混沌因子: 8% 概率随机注入意外事件                       │
│   ├─ 事件去重: 优先选择未使用过的事件                        │
│   └─ 事件构建: 从模板生成事件对象                            │
│                                                              │
│ 工具 (Tools)                                                 │
│   ├─ EVENT_TEMPLATES — 14 种事件模板字典                    │
│   └─ [缺失] LLM 调用（生成事件细节）                        │
│                                                              │
│ 记忆 (Memory)                                                │
│   ├─ state.used_event_ids — 已使用事件集合                  │
│   ├─ state.current_beat — 当前节拍（含事件池）              │
│   └─ _used_events — Agent 内部已使用事件列表                │
└─────────────────────────────────────────────────────────────┘
```

#### 三层实现细节

**大脑 (Brain) — 决策逻辑**

```python
# 文件: game/agents/event_agent.py
# 入口: async def think(self, state: AgentState) -> Dict[str, Any]

# 1. 事件模板池（硬编码）
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

# 2. 事件选择（加权采样）
available = [e for e in beat.event_pool if e not in self._used_events]
if not available:
    available = beat.event_pool  # 全部用过则重置
    self._used_events = []
event_type = random.choice(available)

# 3. 混沌因子（8% 概率随机事件）
if random.random() < 0.08:
    all_events = list(EVENT_TEMPLATES.keys())
    chaos_event = random.choice(all_events)
    if chaos_event != event_type:
        event_type = chaos_event  # 替换为随机事件

# 4. 事件构建（静态模板）
event = {
    "type": event_type,
    "description": EVENT_TEMPLATES.get(event_type, "角色与玩家互动"),
    "scene": state.world.current_scene,
    "time": state.world.current_time,
    "weather": state.world.weather,
    "round": state.total_rounds + 1,
}
```

**工具 (Tools) — 外部能力**

```python
# 当前已实现:
EVENT_TEMPLATES  # 14 种事件模板字典（硬编码）

# 当前缺失:
# - 无 LLM 调用（事件描述是静态模板，不根据角色/场景定制）
# - 无向量检索（不查询历史相似事件）
# - 无情绪状态感知（不根据情绪选择事件）
```

**记忆 (Memory) — 状态访问**

```python
# 读取:
state.current_beat          # 当前 NarrativeBeat（含 event_pool）
state.used_event_ids        # 全局已使用事件集合（set）
state.world.current_scene   # 当前场景
state.world.current_time    # 当前时间段
state.world.weather         # 当前天气
state.total_rounds          # 总轮次

# 写入:
state.pending_event = event              # 设置待处理事件
state.used_event_ids.add(event_type)     # 记录已使用事件
self._used_events.append(event_type)     # Agent 内部记录
```

#### 当前状态: ⭐⭐⭐⭐ 80%

| 功能 | 状态 | 说明 |
|------|------|------|
| 事件模板 | ✅ 完成 | 14 种事件类型 |
| 加权采样 | ✅ 完成 | 未使用事件优先 |
| 混沌因子 | ✅ 完成 | 8% 概率随机事件 |
| 事件去重 | ✅ 完成 | 双层去重（Agent 内 + State 全局） |
| **事件细节生成** | ❌ 未实现 | 事件描述是静态模板 |
| **情绪驱动选择** | ❌ 未实现 | 不根据情绪状态选择事件 |
| **LLM 事件创作** | ❌ 未实现 | 应该用 LLM 生成事件细节 |

#### 差距与优化

```
差距 1: 事件描述是静态模板
  当前: "角色与玩家初次相遇" — 所有角色/场景都一样
  应该: 根据角色性格、场景、情绪生成具体描述
  改动: _build_event() 增加 LLM 调用生成事件细节

差距 2: 不根据情绪选择事件
  当前: 随机采样，与情绪无关
  应该: 高好感度→偏向正面事件，高敌意→偏向冲突事件
  改动: 事件采样增加情绪权重

差距 3: 混沌因子可能导致不合理事件
  当前: 8% 概率从所有事件中随机选
  问题: 可能在悲伤阶段注入"开心"事件
  改动: 混沌事件也应考虑情绪兼容性
```

---

### 3.5 DialogueAgent（对话 Agent）

**职责**: 生成角色台词和玩家选项

#### 三层设计

```
┌─────────────────────────────────────────────────────────────┐
│ DialogueAgent                                                │
├─────────────────────────────────────────────────────────────┤
│ 大脑 (Brain)                                                 │
│   ├─ 台词生成: LLM 生成角色台词（max_tokens=100）            │
│   ├─ 流式输出: think_stream() 支持逐字输出                   │
│   ├─ 选项生成: 硬编码 3 个方向（积极/中性/消极）             │
│   └─ 性格注入: prompt 中注入角色性格关键词                   │
│                                                              │
│ 工具 (Tools)                                                 │
│   ├─ text_gen.generate_dialogue_stream() — 流式 LLM         │
│   ├─ text_gen._call_text_generation() — 同步 LLM            │
│   └─ [缺失] 情绪状态查询（应调整语气）                      │
│                                                              │
│ 记忆 (Memory)                                                │
│   ├─ state.character_name — 角色名                          │
│   ├─ state.character_personality — 性格关键词               │
│   ├─ state.emotion — 当前情绪（未使用）                     │
│   └─ [缺失] 对话风格历史（应保持一致性）                    │
└─────────────────────────────────────────────────────────────┘
```

#### 三层实现细节

**大脑 (Brain) — 决策逻辑**

```python
# 文件: game/agents/dialogue_agent.py
# 入口: async def think(self, state: AgentState) -> Dict[str, Any]

# 1. 构建 prompt（注入角色信息 + 事件上下文）
prompt = self._build_dialogue_prompt(state)
# → 包含: 角色名、性格关键词、事件描述、对话历史、玩家最后输入

# 2. 台词生成（LLM 调用）
character_dialogue = self._generate_dialogue(prompt)
# → 调用 text_gen._call_text_generation(prompt, max_tokens=100, temperature=0.9)
# → 降级: 失败时返回 "{角色名}：..."

# 3. 选项生成（硬编码，无 LLM）
options = self._generate_options(state)
# → 返回固定 3 个方向:
#   [{"id": 0, "text": "积极回应", "direction": "positive"},
#    {"id": 1, "text": "中性回应", "direction": "neutral"},
#    {"id": 2, "text": "消极回应", "direction": "negative"}]

# 4. 流式输出（可选）
async for chunk in self.text_gen.generate_dialogue_stream(prompt, max_tokens=100):
    yield chunk  # 逐字输出
```

**工具 (Tools) — 外部能力**

```python
# 当前已实现:
self.text_gen._call_text_generation(prompt, max_tokens=100, temperature=0.9)
self.text_gen.generate_dialogue_stream(prompt, max_tokens=100, temperature=0.9)

# 当前缺失:
# - 无情绪状态感知（不根据情绪调整语气）
# - 无选项生成 LLM 调用（选项是硬编码的）
# - 无对话风格追踪（不保持一致性）
```

**记忆 (Memory) — 状态访问**

```python
# 读取:
state.character_name          # 角色名（如 "小明"）
state.character_personality   # 性格数据（如 {"keywords": ["温柔", "害羞"]}）
state.emotion                 # EmotionState 对象（当前未使用）
state.last_player_input       # 玩家最后输入
state.dialogue_history        # 对话历史列表
state.pending_event           # 当前事件（含 description）

# 写入:
state.output_dialogue = character_dialogue  # 设置输出台词
state.add_to_history("character", dialogue) # 添加到对话历史
```

#### 当前状态: ⭐⭐⭐⭐⭐ 95%

| 功能 | 状态 | 说明 |
|------|------|------|
| 台词生成 | ✅ 完成 | LLM 生成，max_tokens=100 |
| 流式输出 | ✅ 完成 | think_stream() 支持 |
| 性格注入 | ✅ 完成 | prompt 中注入性格关键词 |
| 选项生成 | ⚠️ 简陋 | 硬编码 3 个方向，不丰富 |
| **情绪语气调整** | ❌ 未实现 | 不根据情绪状态调整语气 |
| **对话风格一致性** | ❌ 未实现 | 不追踪角色的说话风格 |

#### 差距与优化

```
差距 1: 选项是硬编码的
  当前: ["积极回应", "中性回应", "消极回应"]
  应该: 根据剧情/情绪生成具体选项
  改动: _generate_options() 增加 LLM 调用

差距 2: 不根据情绪调整语气
  当前: 同一角色在开心和悲伤时说话方式相同
  应该: 开心时语调上扬，悲伤时语调低沉
  改动: prompt 中注入当前情绪状态描述

差距 3: 不保持对话风格一致性
  当前: 每轮独立生成，可能风格不一致
  应该: 参考最近 3 轮对话保持风格
  改动: prompt 中注入最近对话历史
```

---

### 3.6 ConsistencyAgent（一致性 Agent）

**职责**: 输出前校验所有生成内容

#### 三层设计

```
┌─────────────────────────────────────────────────────────────┐
│ ConsistencyAgent                                             │
├─────────────────────────────────────────────────────────────┤
│ 大脑 (Brain)                                                 │
│   ├─ 情绪突变检测: 变化 > 30 → 违规                         │
│   ├─ 对话内容校验: 长度、重复性、角色名                     │
│   ├─ 事件连续性: 检测连续重复事件                            │
│   └─ [缺失] LLM 逻辑校验                                    │
│                                                              │
│ 工具 (Tools)                                                 │
│   └─ [缺失] LLM 调用（语义级一致性检查）                    │
│                                                              │
│ 记忆 (Memory)                                                │
│   ├─ state.output_emotion_changes — 情绪变化                │
│   ├─ state.output_dialogue — 生成的台词                     │
│   ├─ state.event_history — 事件历史                         │
│   └─ state.consistency_checks — 违规列表                    │
└─────────────────────────────────────────────────────────────┘
```

#### 三层实现细节

**大脑 (Brain) — 决策逻辑**

```python
# 文件: game/agents/consistency_agent.py
# 入口: async def think(self, state: AgentState) -> Dict[str, Any]

violations = []

# 1. 情绪突变检测（阈值判断）
changes = state.output_emotion_changes
for key, delta in changes.items():
    if abs(delta) > 30.0:  # MAX_EMOTION_DELTA
        violations.append(f"情绪[{key}]变化过大: {delta:.1f}")

# 2. 对话内容校验（字符级检查）
dialogue = state.output_dialogue
if state.character_name and state.character_name not in dialogue:
    violations.append("对话缺少角色名")
if len(dialogue.strip()) < 5:
    violations.append("对话内容过短")
if self._is_repetitive(dialogue):  # unique_chars / total_chars < 0.3
    violations.append("对话内容重复度过高")

# 3. 事件连续性检测
if len(state.event_history) >= 2:
    last = state.event_history[-1]
    if event_type and last.get("type") == event_type:
        violations.append(f"连续重复事件: {event_type}")

# 4. 返回结果
return {
    "passed": len(violations) == 0,
    "violations": violations,
    "severity": "error" if len(violations) >= 3 else "warning" if violations else "ok",
}
```

**工具 (Tools) — 外部能力**

```python
# 当前已实现: 无（所有检查都是纯规则）

# 当前缺失:
# - 无 LLM 调用（应做语义级一致性检查）
# - 无向量检索（应查询历史事件做连贯性检查）
# - 无自动修正机制（只检测不修正）
```

**记忆 (Memory) — 状态访问**

```python
# 读取:
state.output_emotion_changes  # 本次情绪变化量（dict）
state.output_dialogue         # 生成的台词文本
state.event_history           # 事件历史列表
state.character_name          # 角色名
state.pending_event           # 当前事件（含 type）

# 写入:
state.consistency_checks = violations  # 违规列表
```

#### 当前状态: ⭐⭐⭐ 70%

| 功能 | 状态 | 说明 |
|------|------|------|
| 情绪突变检测 | ✅ 完成 | 阈值 30 |
| 对话内容校验 | ✅ 完成 | 长度 + 重复性 |
| 事件连续性 | ✅ 完成 | 检测连续重复事件 |
| **角色性格一致性** | ❌ 未实现 | 不检查台词是否符合性格 |
| **剧情逻辑一致性** | ❌ 未实现 | 不检查事件是否合理 |
| **自动修正** | ❌ 未实现 | 只检测不修正 |

#### 差距与优化

```
差距 1: 检查规则太少
  当前: 只有 3 条规则
  应该: 增加角色性格一致性、剧情逻辑、情绪合理性等
  改动: think() 增加更多检查规则

差距 2: 只检测不修正
  当前: 检测到违规后只记录，不修正
  应该: 轻微违规自动修正，严重违规重新生成
  改动: 增加 auto_correct() 方法

差距 3: 无 LLM 语义检查
  当前: 只做字符级检查
  应该: LLM 检查语义一致性
  改动: 增加可选的 LLM 校验调用
```

---

### 3.7 共享基础设施

#### BaseAgent 抽象基类

```python
# 文件: game/agents/base.py
class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"agent.{name}")

    @abstractmethod
    async def think(self, state: AgentState) -> Dict[str, Any]:
        """核心决策：分析状态 → 返回行动"""
        ...

    def observe(self, observation: Dict[str, Any]) -> None:
        """接收外部反馈（可选实现）"""
        pass

    def reset(self) -> None:
        """重置 Agent 内部状态（可选实现）"""
        pass
```

#### AgentState 全局共享状态

```python
# 文件: game/agents/state.py
@dataclass
class AgentState:
    # 基础标识
    thread_id: str
    character_id: int
    character_name: str
    character_personality: Dict[str, Any]

    # 叙事状态
    phase: SessionPhase              # INIT/OPENING/RISING/CLIMAX/RESOLUTION/ENDING/FINISHED
    current_beat: NarrativeBeat      # 当前节拍
    round_count: int                 # 当前事件轮次
    total_rounds: int                # 总轮次

    # 世界状态
    world: WorldState                # scene, time, weather, elapsed_minutes

    # 情绪状态
    emotion: EmotionState            # 12 维情绪

    # 对话历史
    dialogue_history: List[Dict]     # [{role, content, metadata}]
    pending_event: Dict              # 当前事件
    last_character_dialogue: str     # 角色最后台词
    last_player_input: str           # 玩家最后输入

    # 事件追踪
    event_history: List[Dict]        # 事件历史
    used_event_ids: set              # 已使用事件 ID

    # 一致性校验
    consistency_checks: List[str]    # 违规列表

    # 输出缓冲区
    output_dialogue: str             # 输出台词
    output_options: List[Dict]       # 输出选项
    output_scene: str                # 输出场景
    output_scene_image_url: str      # 场景图片 URL
    output_audio_url: str            # 音频 URL
    output_audio_duration: float     # 音频时长
    output_emotion_changes: Dict     # 情绪变化
    output_tts_params: TTSParams     # TTS 参数
```

#### AgentOrchestrator 流水线编排

```python
# 文件: game/agents/orchestrator.py
class AgentOrchestrator:
    # 流水线: Director → World → Emotion → Event → Dialogue → TTS → Consistency

    async def process_input(self, user_input, thread_id):
        state.last_player_input = user_input
        state.advance_round()
        state.add_to_history("player", user_input)

        # 1. Director: 决定剧情走向
        director_result = await self.director.think(state)
        if director_result.get("action") == "end_game":
            return await self._build_ending_output(state)

        # 2. World: 推进世界状态
        world_result = await self.world.think(state)

        # 3. Emotion: 计算情绪变化
        emotion_result = await self.emotion.think(state)

        # 4. Event: 选择事件
        event_result = await self.event.think(state)

        # 5. Dialogue: 生成角色台词
        dialogue_result = await self.dialogue.think(state)

        # 5.5 Image & TTS: 异步生成（不阻塞 pipeline）

        # 6. Consistency: 输出前校验
        consistency_result = await self.consistency.think(state)

        # 7. 构建输出
        return { ... }
```

#### MemoryManager 记忆管理器

```python
# 文件: game/agents/memory.py
class MemoryManager:
    def __init__(self, vector_db=None):
        self.vector_db = vector_db  # ChromaDB 向量数据库

    # 功能:
    # - 事件摘要存储
    # - 对话历史检索
    # - 相似事件查询
    # - 长期记忆管理
```

---

## 四、完成度总览

| Agent | 大脑 | 工具 | 记忆 | 总评 | 最大差距 |
|-------|------|------|------|------|---------|
| DirectorAgent | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | 85% | 无 LLM 推理 |
| WorldSimulator | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | 95% | 场景切换无逻辑 |
| EmotionAgent | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | 60% | **关键词匹配太简单** |
| EventAgent | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | 80% | 事件描述是静态模板 |
| DialogueAgent | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 95% | 选项是硬编码 |
| ConsistencyAgent | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | 70% | 只检测不修正 |

---

## 五、优化路线图

### Phase 1: EmotionAgent 增强（最高优先级）

```
目标: 让情绪系统真正响应玩家选择

改动:
  1. _analyze_player_impact() 接入 LLM
     - Prompt: 分析玩家输入的情感倾向
     - 返回: {favorability: ±N, trust: ±N, ...}
     - 降级: LLM 失败时回退到关键词匹配

  2. 增加上下文感知
     - 将最近 3 轮对话历史传入 prompt
     - 连续正面输入 → 情绪加速上升

  3. 增加性格修正
     - 高冷角色对"我喜欢你"反应更克制
     - 热情角色反应更强烈

  4. 增加情绪趋势追踪
     - 记录最近 N 轮的情绪变化方向
     - 用于 TTS 情感引擎的 trend 参数

预计效果: 情绪响应从 ±2~3 提升到 ±5~15
```

### Phase 2: DirectorAgent 增强

```
目标: 结局判断更自然

改动:
  1. _should_end() 增加情绪极化条件
     - favorability ≥ 85 → 美好结局提前
     - hostility ≥ 70 → 悲剧结局提前
     - favorability ≤ 15 → 崩塌结局提前

  2. 候选评分扩展
     - 增加剧情连贯性评分
     - 增加角色性格匹配评分

预计效果: 结局时机更自然，不再固定 30 分钟
```

### Phase 3: EventAgent + WorldSimulator 增强

```
目标: 事件和场景更贴合剧情

改动:
  1. EventAgent._build_event() 增加 LLM 生成事件细节
  2. EventAgent 事件选择增加情绪权重
  3. WorldSimulator 场景切换增加剧情逻辑
  4. WorldSimulator 天气与情绪联动

预计效果: 事件不再千篇一律，场景切换更合理
```

### Phase 4: DialogueAgent + ConsistencyAgent 增强

```
目标: 对话更丰富，输出更稳定

改动:
  1. DialogueAgent 选项生成接入 LLM
  2. DialogueAgent prompt 注入情绪状态
  3. ConsistencyAgent 增加性格一致性检查
  4. ConsistencyAgent 增加自动修正机制

预计效果: 选项更丰富，台词更符合情绪
```

---

## 六、改进后预期完成度

| Agent | 当前 | Phase 1 后 | Phase 2 后 | Phase 3 后 | Phase 4 后 |
|-------|------|-----------|-----------|-----------|-----------|
| DirectorAgent | 85% | 85% | **95%** | 95% | 95% |
| WorldSimulator | 95% | 95% | 95% | **98%** | 98% |
| EmotionAgent | 60% | **90%** | 90% | 90% | 90% |
| EventAgent | 80% | 80% | 80% | **95%** | 95% |
| DialogueAgent | 95% | 95% | 95% | 95% | **98%** |
| ConsistencyAgent | 70% | 70% | 70% | 70% | **90%** |
| **整体** | **81%** | **86%** | **88%** | **92%** | **95%** |

---

## 七、LLM 调用预算

| Agent | 当前 LLM 调用/轮 | 改进后 LLM 调用/轮 | 说明 |
|-------|-----------------|-------------------|------|
| DirectorAgent | 0 | 0~1（可选） | 结局判断时可选调用 |
| WorldSimulator | 0 | 0 | 纯规则 |
| EmotionAgent | 0 | 1 | 分析玩家输入情感 |
| EventAgent | 0 | 0~1（事件细节） | 事件切换时调用 |
| DialogueAgent | 1 | 1 | 台词生成 |
| ConsistencyAgent | 0 | 0~1（可选） | 语义级校验 |
| **总计** | **1** | **2~4** | 增加 1~3 次/轮 |

**成本影响**: 每局增加约 2000-4000 tokens（+30-50%）
