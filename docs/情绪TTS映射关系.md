# 游戏情绪系统 → TTS 情感映射关系

> 将 NoEndStory 的 12 维情绪状态映射到豆包 TTS 的 10 种情感参数
> 更新日期: 2026-06-17

---

## 一、游戏情绪维度说明

| 维度 | 字段 | 范围 | 默认值 | 含义 |
|------|------|------|--------|------|
| 好感度 | `favorability` | 0-100 | 50 | 对玩家的好感程度 |
| 信任度 | `trust` | 0-100 | 50 | 对玩家的信任程度 |
| 敌意值 | `hostility` | 0-100 | 0 | 对玩家的敌意程度 |
| 情绪值 | `emotion` | 0-100 | 50 | 整体情绪状态（低=消极，高=积极） |
| 压力值 | `stress` | 0-100 | 20 | 当前压力水平 |
| 焦虑值 | `anxiety` | 0-100 | 10 | 当前焦虑水平 |
| 快乐值 | `happiness` | 0-100 | 50 | 当前快乐程度 |
| 悲伤值 | `sadness` | 0-100 | 10 | 当前悲伤程度 |
| 自信值 | `confidence` | 0-100 | 50 | 当前自信程度 |
| 主动性 | `initiative` | 0-100 | 50 | 主动表达意愿 |
| 谨慎度 | `caution` | 0-100 | 50 | 言行谨慎程度 |

---

## 二、TTS 情感参数可选值

| 值 | 中文 | 语调特征 | 适用场景 |
|----|------|---------|---------|
| `happy` | 开心 | 语调上扬，轻快愉悦 | 好感度高、快乐值高 |
| `sad` | 悲伤 | 语调下沉，沉重缓慢 | 悲伤值高、好感度低 |
| `angry` | 生气 | 语速加快，音量提高 | 敌意值高、压力值高 |
| `surprised` | 惊讶 | 语调起伏大 | 突发事件、意外对话 |
| `fear` | 恐惧 | 声音颤抖 | 焦虑值高、压力值高 |
| `hate` | 厌恶 | 语气冷淡带反感 | 敌意值高、信任度低 |
| `excited` | 激动 | 语速快，音量高 | 快乐值高、主动性高 |
| `coldness` | 冷漠 | 平淡无感情 | 好感度低、信任度低 |
| `neutral` | 中性 | 自然状态（默认） | 情绪平稳时 |
| `depressed` | 沮丧 | 低沉缓慢 | 悲伤值高、自信值低 |

---

## 三、核心映射规则

### 3.1 情绪计算公式

```python
def calculate_tts_emotion(emotion_state: EmotionState) -> str:
    """根据 12 维情绪状态计算 TTS 情感参数"""

    fav = emotion_state.favorability      # 好感度 0-100
    trust = emotion_state.trust            # 信任度 0-100
    hostility = emotion_state.hostility    # 敌意值 0-100
    happiness = emotion_state.happiness    # 快乐值 0-100
    sadness = emotion_state.sadness        # 悲伤值 0-100
    stress = emotion_state.stress          # 压力值 0-100
    anxiety = emotion_state.anxiety        # 焦虑值 0-100
    confidence = emotion_state.confidence  # 自信值 0-100
    initiative = emotion_state.initiative  # 主动性 0-100

    # ===== 第一优先级：极端情绪（阈值触发） =====

    # 高敌意 → 生气/厌恶
    if hostility >= 70:
        return 'angry' if stress >= 60 else 'hate'

    # 高焦虑+高压力 → 恐惧
    if anxiety >= 70 and stress >= 60:
        return 'fear'

    # 高悲伤+低自信 → 沮丧
    if sadness >= 70 and confidence <= 30:
        return 'depressed'

    # 高悲伤 → 悲伤
    if sadness >= 60:
        return 'sad'

    # ===== 第二优先级：积极情绪 =====

    # 高快乐+高好感 → 激动/开心
    if happiness >= 70:
        if fav >= 70 and initiative >= 60:
            return 'excited'
        return 'happy'

    # 高好感+高信任 → 开心
    if fav >= 65 and trust >= 60:
        return 'happy'

    # 高主动性+高快乐 → 激动
    if initiative >= 70 and happiness >= 50:
        return 'excited'

    # ===== 第三优先级：消极情绪 =====

    # 低好感+低信任 → 冷漠
    if fav <= 35 and trust <= 40:
        return 'coldness'

    # 低好感+高敌意 → 厌恶
    if fav <= 40 and hostility >= 40:
        return 'hate'

    # 高压力 → 根据其他维度细分
    if stress >= 60:
        if anxiety >= 50:
            return 'fear'
        return 'angry'

    # ===== 默认：中性 =====
    return 'neutral'
```

### 3.2 映射决策树（可视化）

```
                        ┌─ hostility ≥ 70 ─→ angry / hate
                        │
                        ├─ anxiety ≥ 70 & stress ≥ 60 ─→ fear
                        │
                        ├─ sadness ≥ 70 & confidence ≤ 30 ─→ depressed
    EmotionState ───────┤
                        ├─ sadness ≥ 60 ─→ sad
                        │
                        ├─ happiness ≥ 70 ─→ excited / happy
                        │
                        ├─ fav ≥ 65 & trust ≥ 60 ─→ happy
                        │
                        ├─ fav ≤ 35 & trust ≤ 40 ─→ coldness
                        │
                        ├─ stress ≥ 60 ─→ fear / angry
                        │
                        └─ 默认 ─→ neutral
```

---

## 四、好感度 × 情绪值 → TTS 情感速查表

> 横轴：好感度（fav），纵轴：情绪值（emotion）
> 单元格：TTS emotion 参数

|  | fav 0-20 | fav 21-40 | fav 41-60 | fav 61-80 | fav 81-100 |
|--|----------|-----------|-----------|-----------|------------|
| **emotion 0-20** | `hate` | `coldness` | `sad` | `sad` | `depressed` |
| **emotion 21-40** | `angry` | `coldness` | `neutral` | `neutral` | `sad` |
| **emotion 41-60** | `hate` | `neutral` | `neutral` | `happy` | `happy` |
| **emotion 61-80** | `angry` | `neutral` | `happy` | `happy` | `excited` |
| **emotion 81-100** | `angry` | `surprised` | `excited` | `excited` | `excited` |

> ⚠️ 此表为简化版，实际使用时需叠加 stress / anxiety / hostility 修正

---

## 五、语速/音调微调规则

除 `emotion` 参数外，还可通过 `speed_ratio` 和 `pitch_ratio` 增强情感表达：

| TTS 情感 | speed_ratio | pitch_ratio | 说明 |
|---------|-------------|-------------|------|
| `happy` | 1.1 | 1.05 | 稍快稍高，轻快感 |
| `sad` | 0.85 | 0.95 | 放慢降低，沉重感 |
| `angry` | 1.2 | 1.1 | 加快提高，攻击性 |
| `surprised` | 1.15 | 1.15 | 快速高音调，意外感 |
| `fear` | 0.9 | 1.1 | 放慢但音调高，紧张感 |
| `hate` | 0.95 | 0.9 | 略慢略低，冷淡感 |
| `excited` | 1.2 | 1.1 | 快速高音，兴奋感 |
| `coldness` | 0.9 | 0.95 | 放慢降低，无感情 |
| `neutral` | 1.0 | 1.0 | 默认值 |
| `depressed` | 0.8 | 0.9 | 最慢最低，低沉感 |

```python
TTS_EMOTION_PARAMS = {
    'happy':     {'speed_ratio': 1.10, 'pitch_ratio': 1.05},
    'sad':       {'speed_ratio': 0.85, 'pitch_ratio': 0.95},
    'angry':     {'speed_ratio': 1.20, 'pitch_ratio': 1.10},
    'surprised': {'speed_ratio': 1.15, 'pitch_ratio': 1.15},
    'fear':      {'speed_ratio': 0.90, 'pitch_ratio': 1.10},
    'hate':      {'speed_ratio': 0.95, 'pitch_ratio': 0.90},
    'excited':   {'speed_ratio': 1.20, 'pitch_ratio': 1.10},
    'coldness':  {'speed_ratio': 0.90, 'pitch_ratio': 0.95},
    'neutral':   {'speed_ratio': 1.00, 'pitch_ratio': 1.00},
    'depressed': {'speed_ratio': 0.80, 'pitch_ratio': 0.90},
}
```

---

## 六、完整调用流程

```
游戏角色对话生成
  ↓
EmotionAgent 更新 12 维情绪状态
  ↓
calculate_tts_emotion(emotion_state) → emotion 参数
  ↓
TTS_EMOTION_PARAMS[emotion] → speed_ratio / pitch_ratio
  ↓
调用豆包 TTS API（带 emotion + speed + pitch）
  ↓
返回带有情感色彩的语音
```

### 6.1 代码集成示例

```python
# 在 TTS 调用处集成
def generate_speech_with_emotion(text: str, voice_id: str, emotion_state: EmotionState) -> bytes:
    """生成带情感的语音"""

    # 1. 计算 TTS 情感
    emotion = calculate_tts_emotion(emotion_state)

    # 2. 获取语速/音调参数
    params = TTS_EMOTION_PARAMS.get(emotion, TTS_EMOTION_PARAMS['neutral'])

    # 3. 构建请求
    payload = {
        "app": { ... },
        "user": { "uid": "user_001" },
        "audio": {
            "voice_type": voice_id,
            "emotion": emotion,                    # ← 情感参数
            "encoding": "wav",
            "speed_ratio": params['speed_ratio'],  # ← 语速微调
            "pitch_ratio": params['pitch_ratio'],  # ← 音调微调
            "volume_ratio": 1.0,
        },
        "request": {
            "reqid": f"tts_{int(time.time())}",
            "text": text,
            "text_type": "plain",
            "operation": "query"
        }
    }

    # 4. 调用 API
    resp = requests.post(TTS_API_URL, json=payload, timeout=30)
    return resp.json()
```

---

## 七、边界条件处理

| 场景 | 处理方式 |
|------|---------|
| 所有情绪值都在中间区间 (40-60) | 返回 `neutral` |
| 好感度和敌意同时高 (fav>60, hostility>60) | 优先看敌意 → `angry`（矛盾心理） |
| 压力高但焦虑低 | 返回 `angry`（烦躁而非恐惧） |
| 快乐高但好感低 | 返回 `surprised`（意外的开心） |
| 情绪状态全为默认值 | 返回 `neutral` |

---

## 八、测试用例

| 测试场景 | 输入状态 | 预期 emotion | 预期语速 |
|---------|---------|-------------|---------|
| 初次见面（默认状态） | fav=50, trust=50, all=default | `neutral` | 1.0 |
| 好感升温 | fav=75, trust=65, happiness=70 | `happy` | 1.1 |
| 热恋阶段 | fav=90, trust=85, happiness=85, initiative=80 | `excited` | 1.2 |
| 吵架 | fav=30, hostility=75, stress=70 | `angry` | 1.2 |
| 冷战 | fav=25, trust=20, hostility=30 | `coldness` | 0.9 |
| 和好 | fav=60, trust=55, happiness=65 | `happy` | 1.1 |
| 分手边缘 | fav=15, sadness=75, confidence=25 | `depressed` | 0.8 |
| 受到惊吓 | anxiety=80, stress=75 | `fear` | 0.9 |
| 意外惊喜 | fav=60, happiness=80, surprise=true | `surprised` | 1.15 |
| 厌恶排斥 | fav=20, hostility=50, trust=15 | `hate` | 0.95 |

---

## 九、后续扩展方向

1. **动态权重**：不同性格角色对同一情绪状态的表达方式不同（高冷角色即使开心也不会用 `excited`）
2. **情绪过渡**：相邻对话之间情绪变化不应突变，需要插值平滑
3. **场景修正**：严肃场景（课堂、葬礼）压制 `excited`/`happy`，浪漫场景提升 `happy` 权重
4. **混合情感**：支持 `happy+sad`（感动落泪）等复合情感，需 TTS API 支持
