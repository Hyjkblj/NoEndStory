# TTS 情感语音完整方案

> 情绪状态 → 性格修正 → TTS 参数 → 语音输出
> 更新日期: 2026-06-17

---

## 一、系统架构

```
游戏角色对话生成
       ↓
EmotionState（12 维情绪状态）
       ↓
┌──────────────────────────────────────┐
│  TTS 情感计算引擎                     │
│                                      │
│  Step 1: 情绪 → 基础情感评分          │
│  Step 2: 性格关键词 → 情感修正        │
│  Step 3: 选择最高分情感               │
│  Step 4: 情感 → 语速/音调微调         │
│  Step 5: 输出最终 TTS 参数            │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│  豆包 TTS API                        │
│                                      │
│  voice_type: 角色选定的音色           │
│  emotion: 计算得到的情感              │
│  speed_ratio: 计算得到的语速          │
│  pitch_ratio: 计算得到的音调          │
│  volume_ratio: 1.0（固定）            │
└──────────────────────────────────────┘
       ↓
带有情感色彩的语音输出
```

---

## 二、输入数据

### 2.1 情绪状态（来自 EmotionState）

| 维度 | 字段 | 范围 | 默认值 | 含义 |
|------|------|------|--------|------|
| 好感度 | favorability | 0-100 | 50 | 对玩家的好感 |
| 信任度 | trust | 0-100 | 50 | 对玩家的信任 |
| 敌意值 | hostility | 0-100 | 0 | 对玩家的敌意 |
| 情绪值 | emotion | 0-100 | 50 | 整体情绪 |
| 压力值 | stress | 0-100 | 20 | 当前压力 |
| 焦虑值 | anxiety | 0-100 | 10 | 当前焦虑 |
| 快乐值 | happiness | 0-100 | 50 | 当前快乐 |
| 悲伤值 | sadness | 0-100 | 10 | 当前悲伤 |
| 自信值 | confidence | 0-100 | 50 | 当前自信 |
| 主动性 | initiative | 0-100 | 50 | 主动表达意愿 |
| 谨慎度 | caution | 0-100 | 50 | 言行谨慎程度 |

### 2.2 性格关键词（来自角色创建，最多 5 个）

30 个可选关键词，分为 5 组：

| 组别 | 关键词 | 对情感表达的影响 |
|------|--------|---------------|
| 外放型 | 外向、热情、阳光、直率、行动力强 | 放大积极情绪 |
| 内敛型 | 内向、慢热、细腻、谨慎、独立 | 抑制情感表达 |
| 冷感型 | 冷静、高冷、理性、成熟、洒脱 | 大幅抑制，偏冷淡 |
| 情感型 | 感性、温柔、体贴、共情力强、浪漫 | 增强柔和表达 |
| 力量型 | 勇敢、自信、执着、有主见、有责任感 | 减少恐惧/悲伤 |
| 其他 | 幽默、善良、可靠、单纯、好奇心强 | 各有特点 |

### 2.3 TTS 可选情感参数

| 值 | 中文 | 语调特征 |
|----|------|---------|
| happy | 开心 | 语调上扬，轻快愉悦 |
| sad | 悲伤 | 语调下沉，沉重缓慢 |
| angry | 生气 | 语速加快，音量提高 |
| surprised | 惊讶 | 语调起伏大 |
| fear | 恐惧 | 声音颤抖 |
| hate | 厌恶 | 语气冷淡带反感 |
| excited | 激动 | 语速快，音量高 |
| coldness | 冷漠 | 平淡无感情 |
| neutral | 中性 | 自然状态（默认） |
| depressed | 沮丧 | 低沉缓慢 |

---

## 三、计算流程

### Step 1: 情绪 → 基础情感评分（含优先级和边界处理）

```python
def compute_base_emotion_scores(emotion: EmotionState) -> dict[str, float]:
    """将 12 维情绪状态映射到 10 种 TTS 情感的基础分

    包含优先级判定和边界情况处理
    """
    fav = emotion.favorability
    trust = emotion.trust
    hostility = emotion.hostility
    happiness = emotion.happiness
    sadness = emotion.sadness
    stress = emotion.stress
    anxiety = emotion.anxiety
    conf = emotion.confidence
    init = emotion.initiative

    # ===== 边界情况：矛盾状态 =====
    # 高好感 + 高敌意 = 矛盾心理（傲娇、纠结）→ 激动
    if fav >= 60 and hostility >= 40:
        return {
            'happy': 20, 'sad': 20, 'angry': 40, 'fear': 10,
            'hate': 15, 'excited': 50, 'coldness': 5, 'depressed': 10,
            'surprised': 30, 'neutral': 10,
        }

    # 高快乐 + 高悲伤 = 感动/不舍 → 惊讶（复合情感）
    if happiness >= 60 and sadness >= 50:
        return {
            'happy': 45, 'sad': 45, 'angry': 5, 'fear': 5,
            'hate': 0, 'excited': 20, 'coldness': 0, 'depressed': 15,
            'surprised': 25, 'neutral': 10,
        }

    # ===== 标准计算 =====
    scores = {
        # 积极情感
        'happy':    happiness * 0.4 + fav * 0.3 + trust * 0.2 + init * 0.1,
        'excited':  happiness * 0.3 + init * 0.3 + fav * 0.2 + conf * 0.2,

        # 消极情感
        'sad':      sadness * 0.5 + (100 - happiness) * 0.2 + (100 - conf) * 0.2 + (100 - fav) * 0.1,
        'angry':    hostility * 0.4 + stress * 0.3 + (100 - trust) * 0.2 + (100 - fav) * 0.1,
        'fear':     anxiety * 0.4 + stress * 0.3 + (100 - conf) * 0.2 + (100 - init) * 0.1,
        'depressed': sadness * 0.4 + (100 - conf) * 0.3 + (100 - happiness) * 0.2 + (100 - init) * 0.1,

        # 关系情感
        'hate':     hostility * 0.5 + (100 - trust) * 0.3 + (100 - fav) * 0.2,
        'coldness': (100 - fav) * 0.3 + (100 - trust) * 0.3 + (100 - happiness) * 0.2 + (100 - init) * 0.2,

        # 特殊情感
        'surprised': 0,  # 由外部事件触发

        # 兜底
        'neutral':  30.0,
    }

    # ===== 优先级修正 =====
    # 高敌意优先压制积极情感
    if hostility >= 50:
        scores['happy'] *= 0.5
        scores['excited'] *= 0.5
        scores['angry'] *= 1.3
        scores['hate'] *= 1.3

    # 高悲伤压制积极情感
    if sadness >= 60:
        scores['happy'] *= 0.6
        scores['excited'] *= 0.6
        scores['sad'] *= 1.2
        scores['depressed'] *= 1.2

    # 高焦虑压制冷静和快乐
    if anxiety >= 60:
        scores['coldness'] *= 0.7
        scores['happy'] *= 0.8
        scores['fear'] *= 1.3

    return scores
```

### Step 2: 性格关键词修正

```python
# 性格关键词 → 情感修正系数表
PERSONALITY_MODIFIERS = {
    '外向':    {'excited': +15, 'happy': +10, 'angry': +5, 'sad': -5, 'fear': -10, 'coldness': -15},
    '内向':    {'excited': -15, 'happy': -5, 'angry': -5, 'sad': +5, 'fear': +5, 'coldness': +10},
    '温柔':    {'excited': 0, 'happy': +10, 'angry': -15, 'sad': +10, 'fear': 0, 'coldness': -15},
    '冷静':    {'excited': -20, 'happy': -10, 'angry': -15, 'sad': -5, 'fear': -15, 'coldness': +20},
    '热情':    {'excited': +20, 'happy': +15, 'angry': 0, 'sad': -5, 'fear': -10, 'coldness': -20},
    '理性':    {'excited': -15, 'happy': -5, 'angry': -10, 'sad': -10, 'fear': -10, 'coldness': +15},
    '感性':    {'excited': +10, 'happy': +15, 'angry': +5, 'sad': +15, 'fear': +5, 'coldness': -15},
    '幽默':    {'excited': +10, 'happy': +15, 'angry': -5, 'sad': -5, 'fear': -10, 'coldness': -10},
    '直率':    {'excited': +10, 'happy': +5, 'angry': +10, 'sad': -5, 'fear': -10, 'coldness': -5},
    '细腻':    {'excited': -5, 'happy': +5, 'angry': -10, 'sad': +10, 'fear': +10, 'coldness': 0},
    '勇敢':    {'excited': +10, 'happy': +5, 'angry': +10, 'sad': -10, 'fear': -20, 'coldness': 0},
    '谨慎':    {'excited': -10, 'happy': -5, 'angry': -10, 'sad': +5, 'fear': +10, 'coldness': +5},
    '自信':    {'excited': +15, 'happy': +10, 'angry': +5, 'sad': -15, 'fear': -20, 'coldness': -5},
    '慢热':    {'excited': -15, 'happy': -10, 'angry': -5, 'sad': +5, 'fear': +5, 'coldness': +15},
    '独立':    {'excited': -10, 'happy': -5, 'angry': -5, 'sad': 0, 'fear': -5, 'coldness': +10},
    '可靠':    {'excited': 0, 'happy': +5, 'angry': -5, 'sad': -5, 'fear': -5, 'coldness': +5},
    '善良':    {'excited': +5, 'happy': +10, 'angry': -15, 'sad': +5, 'fear': 0, 'coldness': -10},
    '体贴':    {'excited': 0, 'happy': +10, 'angry': -10, 'sad': +10, 'fear': +5, 'coldness': -10},
    '执着':    {'excited': +5, 'happy': +5, 'angry': +10, 'sad': +5, 'fear': -5, 'coldness': -5},
    '洒脱':    {'excited': -10, 'happy': +5, 'angry': -10, 'sad': -15, 'fear': -15, 'coldness': +10},
    '高冷':    {'excited': -25, 'happy': -15, 'angry': -10, 'sad': -10, 'fear': -20, 'coldness': +25},
    '阳光':    {'excited': +15, 'happy': +15, 'angry': -5, 'sad': -10, 'fear': -15, 'coldness': -20},
    '成熟':    {'excited': -15, 'happy': -5, 'angry': -10, 'sad': -5, 'fear': -10, 'coldness': +15},
    '单纯':    {'excited': +10, 'happy': +15, 'angry': -10, 'sad': +5, 'fear': +5, 'coldness': -15},
    '有主见':  {'excited': +5, 'happy': +5, 'angry': +10, 'sad': -10, 'fear': -15, 'coldness': +5},
    '共情力强': {'excited': +5, 'happy': +10, 'angry': -5, 'sad': +15, 'fear': +10, 'coldness': -15},
    '行动力强': {'excited': +10, 'happy': +5, 'angry': +5, 'sad': -5, 'fear': -10, 'coldness': -10},
    '好奇心强': {'excited': +10, 'happy': +10, 'angry': 0, 'sad': -5, 'fear': -5, 'coldness': -10},
    '有责任感': {'excited': 0, 'happy': +5, 'angry': +5, 'sad': -5, 'fear': -5, 'coldness': +5},
    '浪漫':    {'excited': +15, 'happy': +15, 'angry': -10, 'sad': +10, 'fear': -5, 'coldness': -20},
}


def apply_personality_modifiers(
    base_scores: dict[str, float],
    personality_keywords: list[str],
) -> dict[str, float]:
    """应用性格修正系数（取所有关键词的平均值）"""
    if not personality_keywords:
        return base_scores

    total_mods: dict[str, float] = {}
    count = 0

    for keyword in personality_keywords:
        if keyword in PERSONALITY_MODIFIERS:
            for emotion, value in PERSONALITY_MODIFIERS[keyword].items():
                total_mods[emotion] = total_mods.get(emotion, 0) + value
            count += 1

    if count == 0:
        return base_scores

    # 取平均值
    avg_mods = {emotion: total / count for emotion, total in total_mods.items()}

    # 应用修正
    result = base_scores.copy()
    for emotion, modifier in avg_mods.items():
        if emotion in result:
            result[emotion] += modifier

    return result
```

### Step 3: 选择最高分情感

```python
def select_best_emotion(scores: dict[str, float]) -> str:
    """选择得分最高的情感"""
    # 确保分数在合理范围
    for emotion in scores:
        scores[emotion] = max(0, min(100, scores[emotion]))

    return max(scores, key=scores.get)
```

### Step 4: 情感 → 语速/音调微调

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

### Step 5: 输出最终参数

```python
@dataclass
class TTSParams:
    """最终 TTS 参数"""
    emotion: str          # 情感标签
    speed_ratio: float    # 语速 0.5-2.0
    pitch_ratio: float    # 音调 0.5-2.0
    volume_ratio: float   # 音量 0.1-2.0（固定 1.0）
    confidence: float     # 情感评分置信度（最高分 / 总分）
```

---

## 四、完整计算函数

```python
def calculate_tts_params(
    emotion_state: EmotionState,
    personality_keywords: list[str],
) -> TTSParams:
    """完整的 TTS 参数计算

    Args:
        emotion_state: 12 维情绪状态
        personality_keywords: 角色性格关键词列表（最多 5 个）

    Returns:
        TTSParams 包含 emotion, speed_ratio, pitch_ratio, volume_ratio, confidence
    """
    # Step 1: 基础情感评分
    base_scores = compute_base_emotion_scores(emotion_state)

    # Step 2: 性格修正
    adjusted_scores = apply_personality_modifiers(base_scores, personality_keywords)

    # Step 3: 选择最高分情感
    best_emotion = select_best_emotion(adjusted_scores)

    # Step 4: 获取语速/音调
    params = TTS_EMOTION_PARAMS.get(best_emotion, TTS_EMOTION_PARAMS['neutral'])

    # Step 5: 计算置信度（排除 neutral 基础分，避免稀释）
    scores_without_neutral = {k: v for k, v in adjusted_scores.items() if k != 'neutral'}
    total = sum(scores_without_neutral.values())
    confidence = scores_without_neutral.get(best_emotion, 0) / total if total > 0 else 0

    # 低置信度降级
    if confidence < 0.15:
        best_emotion = 'neutral'
        params = TTS_EMOTION_PARAMS['neutral']

    return TTSParams(
        emotion=best_emotion,
        speed_ratio=params['speed_ratio'],
        pitch_ratio=params['pitch_ratio'],
        volume_ratio=1.0,
        confidence=confidence,
    )
```

---

## 五、边界条件处理

| 场景 | 处理方式 | 代码位置 |
|------|---------|---------|
| 所有情绪值都在中间区间 (40-60) | 返回 neutral，语速/音调正常 | Step 1: neutral 基础分 30 最高 |
| 好感度和敌意同时高 (fav≥60, hostility≥40) | 返回 excited（矛盾心理/傲娇） | Step 1: 边界情况特殊处理 |
| 高快乐 + 高悲伤 (happiness≥60, sadness≥50) | 返回 surprised（感动/复合情感） | Step 1: 边界情况特殊处理 |
| 高敌意 (hostility≥50) | 压制 happy/excited，增强 angry/hate | Step 1: 优先级修正 |
| 高悲伤 (sadness≥60) | 压制 happy/excited，增强 sad/depressed | Step 1: 优先级修正 |
| 高焦虑 (anxiety≥60) | 压制 coldness/happy，增强 fear | Step 1: 优先级修正 |
| 性格关键词为空 | 使用纯情绪计算，无修正 | Step 2: 直接返回 |
| 关键词互相矛盾（外向+内向） | 修正系数相互抵消，接近中性 | Step 2: 取平均值 |
| 置信度过低（<0.15） | 降级为 neutral（情感不明确） | Step 5: 低置信度降级 |
| 音色不支持 emotion 参数 | 只用 speed_ratio + pitch_ratio 模拟 | API 调用: 降级方案 |
| API 调用失败 | 去掉 emotion 参数重试 | API 调用: 重试机制 |

---

## 六、情绪趋势扩展（可选增强）

### 6.1 问题描述

当前方案只看情绪快照，无法区分：
- 「从 90 降到 60 的快乐」（失落）vs「从 30 升到 60 的快乐」（渐入佳境）
- 「持续高压」（疲惫）vs「刚刚受压」（紧张）

### 6.2 趋势数据结构（可选）

```python
@dataclass
class EmotionTrend:
    """情绪变化趋势（最近 N 轮的变化方向）"""
    delta_favorability: float = 0.0   # 好感度变化（正=上升，负=下降）
    delta_happiness: float = 0.0      # 快乐值变化
    delta_hostility: float = 0.0      # 敌意值变化
    delta_sadness: float = 0.0        # 悲伤值变化
    delta_stress: float = 0.0         # 压力值变化
    trend_strength: float = 0.0       # 趋势强度（0-1，变化幅度越大越强）
```

### 6.3 趋势修正系数（可选）

```python
TREND_MODIFIERS = {
    # 好感度快速上升 → 更积极
    'favorability_rising': {'happy': +10, 'excited': +8, 'sad': -5},
    # 好感度快速下降 → 更消极
    'favorability_falling': {'sad': +10, 'coldness': +8, 'happy': -10},
    # 快乐值快速上升 → 激动
    'happiness_rising': {'excited': +12, 'happy': +8},
    # 快乐值快速下降 → 沮丧
    'happiness_falling': {'depressed': +10, 'sad': +8, 'happy': -10},
    # 敌意快速上升 → 生气
    'hostility_rising': {'angry': +15, 'hate': +10, 'happy': -10},
    # 压力持续高 → 疲惫（冷漠）
    'stress_sustained': {'coldness': +10, 'fear': +5, 'excited': -10},
}


def apply_trend_modifiers(
    scores: dict[str, float],
    trend: EmotionTrend,
) -> dict[str, float]:
    """应用情绪趋势修正"""
    result = scores.copy()
    threshold = 15  # 变化超过 15 才触发趋势修正

    if trend.delta_favorability > threshold:
        for emotion, mod in TREND_MODIFIERS['favorability_rising'].items():
            result[emotion] = result.get(emotion, 0) + mod * trend.trend_strength
    elif trend.delta_favorability < -threshold:
        for emotion, mod in TREND_MODIFIERS['favorability_falling'].items():
            result[emotion] = result.get(emotion, 0) + mod * trend.trend_strength

    if trend.delta_happiness > threshold:
        for emotion, mod in TREND_MODIFIERS['happiness_rising'].items():
            result[emotion] = result.get(emotion, 0) + mod * trend.trend_strength
    elif trend.delta_happiness < -threshold:
        for emotion, mod in TREND_MODIFIERS['happiness_falling'].items():
            result[emotion] = result.get(emotion, 0) + mod * trend.trend_strength

    if trend.delta_hostility > threshold:
        for emotion, mod in TREND_MODIFIERS['hostility_rising'].items():
            result[emotion] = result.get(emotion, 0) + mod * trend.trend_strength

    if trend.delta_stress > 30:  # 压力持续高（阈值更高）
        for emotion, mod in TREND_MODIFIERS['stress_sustained'].items():
            result[emotion] = result.get(emotion, 0) + mod * trend.trend_strength

    return result
```

### 6.4 集成到主函数（可选）

```python
def calculate_tts_params(
    emotion_state: EmotionState,
    personality_keywords: list[str],
    emotion_trend: Optional[EmotionTrend] = None,  # 可选
) -> TTSParams:
    # Step 1: 基础评分
    base_scores = compute_base_emotion_scores(emotion_state)

    # Step 1.5: 趋势修正（如果提供）
    if emotion_trend:
        base_scores = apply_trend_modifiers(base_scores, emotion_trend)

    # Step 2-5: 同前...
```

### 6.5 趋势计算方法（可选）

```python
def compute_emotion_trend(
    current: EmotionState,
    history: list[EmotionState],  # 最近 N 轮的情绪快照
    window: int = 3,              # 计算窗口（最近 3 轮）
) -> EmotionTrend:
    """计算情绪变化趋势"""
    if not history or len(history) < 2:
        return EmotionTrend()

    recent = history[-window:]
    first = recent[0]

    delta_fav = current.favorability - first.favorability
    delta_hap = current.happiness - first.happiness
    delta_hos = current.hostility - first.hostility
    delta_sad = current.sadness - first.sadness
    delta_stress = current.stress - first.stress

    # 趋势强度：变化幅度越大越强（归一化到 0-1）
    max_delta = max(abs(delta_fav), abs(delta_hap), abs(delta_hos), abs(delta_sad))
    strength = min(1.0, max_delta / 50)  # 变化 50 点 = 最大强度

    return EmotionTrend(
        delta_favorability=delta_fav,
        delta_happiness=delta_hap,
        delta_hostility=delta_hos,
        delta_sadness=delta_sad,
        delta_stress=delta_stress,
        trend_strength=strength,
    )
```

---

## 七、与豆包 TTS API 的集成

### 7.1 API 请求格式

```json
{
    "app": {
        "appid": "{APP_ID}",
        "token": "{ACCESS_TOKEN}",
        "cluster": "volcano_tts"
    },
    "user": {
        "uid": "user_001"
    },
    "audio": {
        "voice_type": "{角色选定的音色 Voice ID}",
        "emotion": "{计算得到的情感}",
        "encoding": "wav",
        "speed_ratio": {计算得到的语速},
        "pitch_ratio": {计算得到的音调},
        "volume_ratio": 1.0
    },
    "request": {
        "reqid": "tts_{timestamp}_{hash}",
        "text": "{角色台词文本}",
        "text_type": "plain",
        "operation": "query"
    }
}
```

### 7.2 集成代码（含降级方案）

```python
def generate_emotional_speech(
    text: str,
    voice_id: str,
    emotion_state: EmotionState,
    personality_keywords: list[str],
    tts_config: dict,
) -> Optional[bytes]:
    """生成带情感的语音（含降级方案）

    降级策略：
    1. 音色支持 emotion 参数 → 使用完整情感参数
    2. 音色不支持 emotion → 只用 speed_ratio + pitch_ratio 模拟
    3. API 调用失败 → 使用默认参数重试
    """
    import re, time, base64

    # 1. 计算 TTS 参数
    tts_params = calculate_tts_params(emotion_state, personality_keywords)

    # 2. 文本预处理
    clean_text = re.sub(r'^[^:：]+[：:]', '', text).strip()
    if not clean_text:
        clean_text = text
    if len(clean_text) > 600:
        clean_text = clean_text[:600]

    # 3. 判断音色是否支持 emotion 参数
    supports_emotion = '_emo_' in voice_id  # 多情感音色 ID 包含 _emo_

    # 4. 构建请求
    reqid = f"tts_{int(time.time())}_{hash(text) % 10000}"

    audio_config = {
        "voice_type": voice_id,
        "encoding": "wav",
        "speed_ratio": tts_params.speed_ratio,
        "pitch_ratio": tts_params.pitch_ratio,
        "volume_ratio": tts_params.volume_ratio,
    }

    # 只有支持 emotion 的音色才传入该参数
    if supports_emotion:
        audio_config["emotion"] = tts_params.emotion

    payload = {
        "app": {
            "appid": tts_config['app_id'],
            "token": tts_config['access_token'],
            "cluster": "volcano_tts"
        },
        "user": {"uid": "user_001"},
        "audio": audio_config,
        "request": {
            "reqid": reqid,
            "text": clean_text,
            "text_type": "plain",
            "operation": "query"
        }
    }

    # 5. 调用 API（带重试）
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer; {tts_config['access_token']}"
    }

    for attempt in range(2):  # 最多重试 1 次
        try:
            resp = requests.post(
                tts_config['api_url'],
                headers=headers,
                json=payload,
                timeout=30,
            )

            data = resp.json()
            if data.get("code") == 3000:
                return base64.b64decode(data["data"])
            else:
                logger.warning(f"TTS 合成失败: code={data.get('code')}, msg={data.get('message')}")

                # 降级：如果带 emotion 参数失败，去掉 emotion 重试
                if supports_emotion and attempt == 0:
                    logger.info("降级：去掉 emotion 参数重试")
                    audio_config.pop("emotion", None)
                    continue

                return None
        except Exception as e:
            logger.error(f"TTS 请求异常: {e}")
            if attempt == 0:
                continue
            return None

    return None
```

---

## 八、实际效果示例

### 8.1 同一角色不同情绪

角色：温柔学姐（性格：温柔、体贴、感性）
音色：柔美女友 `zh_female_linjuayi_emo_v2_mars_bigtts`

| 情绪状态 | 计算情感 | 语速 | 音调 | 效果 |
|---------|---------|------|------|------|
| fav=70, happiness=70 | happy | 1.10 | 1.05 | 轻快愉悦的「今天真开心呀」 |
| fav=30, sadness=70 | sad | 0.85 | 0.95 | 低沉缓慢的「我有点难过...」 |
| fav=50, stress=70 | angry | 1.20 | 1.10 | 急促的「你怎么能这样！」 |
| fav=50, all=50 | neutral | 1.00 | 1.00 | 自然的「你好呀」 |

### 8.2 同一情绪不同角色

情绪状态：fav=70, happiness=70, trust=60

| 角色 | 性格关键词 | 计算情感 | 语速 | 音调 | 效果 |
|------|-----------|---------|------|------|------|
| 阳光少年 | 外向、阳光、热情 | excited | 1.20 | 1.10 | 兴奋的「太棒了！」 |
| 高冷御姐 | 高冷、冷静、成熟 | coldness | 0.90 | 0.95 | 平淡的「嗯，还行」 |
| 温柔学姐 | 温柔、体贴、感性 | happy | 1.10 | 1.05 | 温暖的「真好呢」 |
| 冰山总裁 | 高冷、理性、独立 | coldness | 0.90 | 0.95 | 冷淡的「知道了」 |

### 8.3 情感强度与置信度

| 场景 | 情感 | 置信度 | 说明 |
|------|------|--------|------|
| fav=80, happiness=80, hostility=5 | happy | 0.45 | 高置信度，明确的开心 |
| fav=50, happiness=50, all=50 | neutral | 0.35 | 中置信度，平淡状态 |
| fav=45, hostility=40, sadness=30 | 混合 | 0.22 | 低置信度，情感矛盾 |

**低置信度处理**：当置信度 < 0.15 时，降级为 neutral，避免误判。

---

## 九、性能与成本

| 指标 | 值 |
|------|-----|
| 计算耗时 | < 1ms（纯规则，无 LLM 调用） |
| 内存占用 | < 10KB（系数表常驻内存） |
| TTS API 延迟 | 1-3 秒（网络请求） |
| 每局 TTS 调用数 | 约 15-25 次（每轮 1 次） |
| 每局 TTS Token | 约 1500-2500 字符 |

---

## 十、配置与调优

### 10.1 环境变量

```env
# TTS 情感系统开关
TTS_EMOTION_ENABLED=true

# 置信度阈值（低于此值降级为 neutral）
TTS_EMOTION_CONFIDENCE_THRESHOLD=0.15

# 语速范围限制
TTS_SPEED_MIN=0.7
TTS_SPEED_MAX=1.3

# 音调范围限制
TTS_PITCH_MIN=0.85
TTS_PITCH_MAX=1.15
```

### 10.2 调优建议

| 参数 | 调整方向 | 效果 |
|------|---------|------|
| speed_ratio 范围缩小 | 0.8-1.2 → 0.9-1.1 | 语速变化更自然，不突兀 |
| pitch_ratio 范围缩小 | 0.9-1.1 → 0.95-1.05 | 音调变化更细腻 |
| 置信度阈值提高 | 0.15 → 0.25 | 更多情况降级为 neutral，更稳定 |
| 性格修正系数缩小 | ±25 → ±15 | 性格影响更温和 |

---

## 十一、与动态剧本系统的集成

```
动态剧本系统（script_engine）:
  GameController.process_player_choice()
    → RuleEngine 计算情绪变化
    → 更新 EmotionState
    → AI Creator 生成台词
       ↓
TTS 情感系统:
  calculate_tts_params(emotion_state, personality_keywords)
    → 输出 TTSParams
       ↓
TTS API 调用:
  generate_emotional_speech(text, voice_id, tts_params)
    → 返回带情感的语音
       ↓
前端播放
```

### 集成点

```python
# 在 GameController 中集成
class GameController:
    def process_player_choice(self, state, option_id):
        # ... 情绪计算 ...

        # 生成台词
        dialogue = self.ai_creator.generate_dialogue(...)

        # 计算 TTS 参数
        tts_params = calculate_tts_params(
            state.emotion,
            state.character_personality,
        )

        # 生成语音（异步，不阻塞响应）
        audio_future = executor.submit(
            generate_emotional_speech,
            dialogue,
            voice_id,
            tts_params,
            tts_config,
        )

        return {
            'character_dialogue': dialogue,
            'player_options': options,
            'tts_params': {
                'emotion': tts_params.emotion,
                'speed_ratio': tts_params.speed_ratio,
                'pitch_ratio': tts_params.pitch_ratio,
            },
            # 音频通过异步推送或轮询获取
        }
```
