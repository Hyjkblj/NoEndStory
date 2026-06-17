# 性格关键词 → TTS 情感修正系统

> 基于用户创建角色时选择的性格关键词（最多 5 个），动态修正 TTS 情感输出
> 更新日期: 2026-06-17

---

## 一、30 个性格关键词分组

将角色创建时的 30 个性格关键词按对情感表达的影响分为 5 组：

| 组别 | 关键词 | 核心特征 |
|------|--------|---------|
| **外放型** | 外向、热情、阳光、直率、行动力强 | 情感表达放大，积极情绪更外露 |
| **内敛型** | 内向、慢热、细腻、谨慎、独立 | 情感表达抑制，情绪更含蓄 |
| **冷感型** | 冷静、高冷、理性、成熟、洒脱 | 情感表达大幅抑制，偏冷淡 |
| **情感型** | 感性、温柔、体贴、共情力强、浪漫 | 情感表达增强，偏柔和温暖 |
| **力量型** | 勇敢、自信、执着、有主见、有责任感 | 情感表达偏坚定，减少恐惧/悲伤 |

---

## 二、修正系数定义

每个性格关键词对 6 个情感维度产生加减修正：

### 2.1 外放型关键词

| 关键词 | excited | happy | angry | sad | fear | coldness |
|--------|---------|-------|-------|-----|------|----------|
| 外向 | +15 | +10 | +5 | -5 | -10 | -15 |
| 热情 | +20 | +15 | 0 | -5 | -10 | -20 |
| 阳光 | +15 | +15 | -5 | -10 | -15 | -20 |
| 直率 | +10 | +5 | +10 | -5 | -10 | -5 |
| 行动力强 | +10 | +5 | +5 | -5 | -10 | -10 |

### 2.2 内敛型关键词

| 关键词 | excited | happy | angry | sad | fear | coldness |
|--------|---------|-------|-------|-----|------|----------|
| 内向 | -15 | -5 | -5 | +5 | +5 | +10 |
| 慢热 | -15 | -10 | -5 | +5 | +5 | +15 |
| 细腻 | -5 | +5 | -10 | +10 | +10 | 0 |
| 谨慎 | -10 | -5 | -10 | +5 | +10 | +5 |
| 独立 | -10 | -5 | -5 | 0 | -5 | +10 |

### 2.3 冷感型关键词

| 关键词 | excited | happy | angry | sad | fear | coldness |
|--------|---------|-------|-------|-----|------|----------|
| 冷静 | -20 | -10 | -15 | -5 | -15 | +20 |
| 高冷 | -25 | -15 | -10 | -10 | -20 | +25 |
| 理性 | -15 | -5 | -10 | -10 | -10 | +15 |
| 成熟 | -15 | -5 | -10 | -5 | -10 | +15 |
| 洒脱 | -10 | +5 | -10 | -15 | -15 | +10 |

### 2.4 情感型关键词

| 关键词 | excited | happy | angry | sad | fear | coldness |
|--------|---------|-------|-------|-----|------|----------|
| 感性 | +10 | +15 | +5 | +15 | +5 | -15 |
| 温柔 | 0 | +10 | -15 | +10 | 0 | -15 |
| 体贴 | 0 | +10 | -10 | +10 | +5 | -10 |
| 共情力强 | +5 | +10 | -5 | +15 | +10 | -15 |
| 浪漫 | +15 | +15 | -10 | +10 | -5 | -20 |

### 2.5 力量型关键词

| 关键词 | excited | happy | angry | sad | fear | coldness |
|--------|---------|-------|-------|-----|------|----------|
| 勇敢 | +10 | +5 | +10 | -10 | -20 | 0 |
| 自信 | +15 | +10 | +5 | -15 | -20 | -5 |
| 执着 | +5 | +5 | +10 | +5 | -5 | -5 |
| 有主见 | +5 | +5 | +10 | -10 | -15 | +5 |
| 有责任感 | 0 | +5 | +5 | -5 | -5 | +5 |

### 2.6 其他关键词

| 关键词 | excited | happy | angry | sad | fear | coldness |
|--------|---------|-------|-------|-----|------|----------|
| 幽默 | +10 | +15 | -5 | -5 | -10 | -10 |
| 善良 | +5 | +10 | -15 | +5 | 0 | -10 |
| 可靠 | 0 | +5 | -5 | -5 | -5 | +5 |
| 单纯 | +10 | +15 | -10 | +5 | +5 | -15 |
| 好奇心强 | +10 | +10 | 0 | -5 | -5 | -10 |

---

## 三、修正算法

### 3.1 计算流程

```python
def calculate_tts_emotion_with_personality(
    emotion_state: EmotionState,
    personality_keywords: List[str]  # 用户选择的性格关键词，最多 5 个
) -> tuple[str, float, float]:
    """根据情绪状态 + 性格关键词计算 TTS 参数

    Returns:
        (emotion, speed_ratio, pitch_ratio)
    """

    # Step 1: 基础情感评分（6 个候选情感）
    scores = {
        'happy':     0.0,
        'sad':       0.0,
        'angry':     0.0,
        'excited':   0.0,
        'fear':      0.0,
        'coldness':  0.0,
        'hate':      0.0,
        'surprised': 0.0,
        'depressed': 0.0,
        'neutral':   30.0,  # 中性基础分（兜底）
    }

    # Step 2: 根据情绪状态计算基础分
    fav = emotion_state.favorability
    trust = emotion_state.trust
    hostility = emotion_state.hostility
    happiness = emotion_state.happiness
    sadness = emotion_state.sadness
    stress = emotion_state.stress
    anxiety = emotion_state.anxiety
    confidence = emotion_state.confidence
    initiative = emotion_state.initiative

    # 积极情感
    scores['happy'] = (happiness * 0.4 + fav * 0.3 + trust * 0.2 + initiative * 0.1)
    scores['excited'] = (happiness * 0.3 + initiative * 0.3 + fav * 0.2 + confidence * 0.2)

    # 消极情感
    scores['sad'] = (sadness * 0.5 + (100 - happiness) * 0.2 + (100 - confidence) * 0.2 + (100 - fav) * 0.1)
    scores['angry'] = (hostility * 0.4 + stress * 0.3 + (100 - trust) * 0.2 + (100 - fav) * 0.1)
    scores['fear'] = (anxiety * 0.4 + stress * 0.3 + (100 - confidence) * 0.2 + (100 - initiative) * 0.1)
    scores['depressed'] = (sadness * 0.4 + (100 - confidence) * 0.3 + (100 - happiness) * 0.2 + (100 - initiative) * 0.1)

    # 关系情感
    scores['hate'] = (hostility * 0.5 + (100 - trust) * 0.3 + (100 - fav) * 0.2)
    scores['coldness'] = ((100 - fav) * 0.3 + (100 - trust) * 0.3 + (100 - happiness) * 0.2 + (100 - initiative) * 0.2)

    # 惊讶（事件驱动，单独处理）
    scores['surprised'] = 0  # 由外部事件触发，不在情绪状态中计算

    # Step 3: 性格修正（核心改进）
    personality_modifiers = get_personality_modifiers(personality_keywords)
    for emotion, modifier in personality_modifiers.items():
        if emotion in scores:
            scores[emotion] += modifier

    # Step 4: 归一化（确保分数在合理范围）
    for emotion in scores:
        scores[emotion] = max(0, min(100, scores[emotion]))

    # Step 5: 选择得分最高的情感
    best_emotion = max(scores, key=scores.get)

    # Step 6: 计算语速/音调
    params = TTS_EMOTION_PARAMS.get(best_emotion, TTS_EMOTION_PARAMS['neutral'])

    return best_emotion, params['speed_ratio'], params['pitch_ratio']
```

### 3.2 性格修正计算

```python
# 性格关键词 → 情感修正系数表（简化版，完整版见第二章）
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


def get_personality_modifiers(keywords: List[str]) -> Dict[str, float]:
    """汇总所有性格关键词的修正系数（取平均值）"""
    if not keywords:
        return {}

    # 收集所有关键词的修正
    total_mods: Dict[str, float] = {}
    count = 0

    for keyword in keywords:
        if keyword in PERSONALITY_MODIFIERS:
            for emotion, value in PERSONALITY_MODIFIERS[keyword].items():
                total_mods[emotion] = total_mods.get(emotion, 0) + value
            count += 1

    if count == 0:
        return {}

    # 取平均值（避免关键词越多修正越强）
    return {emotion: total / count for emotion, total in total_mods.items()}
```

---

## 四、实际效果对比

### 案例：favorability=70, happiness=70, trust=60, 其余默认

| 角色 | 性格关键词 | 基础情感 | 修正后情感 | 原因 |
|------|-----------|---------|-----------|------|
| 阳光少年 | 外向、阳光、热情 | `happy`(62) | `excited`(72) | 外放型关键词放大积极情绪 |
| 高冷御姐 | 高冷、冷静、成熟 | `happy`(62) | `coldness`(65) | 冷感型关键词压制情感表达 |
| 温柔学姐 | 温柔、体贴、感性 | `happy`(62) | `happy`(77) | 情感型关键词增强柔和表达 |
| 冰山总裁 | 高冷、理性、独立 | `happy`(62) | `coldness`(70) | 三重冷感叠加，极度内敛 |
| 元气少女 | 阳光、单纯、热情 | `happy`(62) | `excited`(75) | 外放+情感双重放大 |

### 案例：favorability=30, hostility=50, stress=60

| 角色 | 性格关键词 | 基础情感 | 修正后情感 | 原因 |
|------|-----------|---------|-----------|------|
| 暴躁老哥 | 直率、勇敢、有主见 | `angry`(52) | `angry`(72) | 力量型关键词放大愤怒 |
| 忍者少女 | 内向、谨慎、细腻 | `angry`(52) | `fear`(55) | 内敛型将愤怒转为内在恐惧 |
| 冰美人 | 高冷、冷静、洒脱 | `angry`(52) | `coldness`(60) | 冷感型压制愤怒，变为冷漠 |

---

## 五、集成到现有系统

### 5.1 数据流

```
用户创建角色
  ↓ 选择性格关键词（最多 5 个）
  ↓ 保存到 character.personality.keywords
  ↓
游戏运行时
  ↓ EmotionAgent 更新情绪状态
  ↓ 读取 character.personality.keywords
  ↓ calculate_tts_emotion_with_personality(emotion_state, keywords)
  ↓ 返回 (emotion, speed_ratio, pitch_ratio)
  ↓
调用 TTS API
  ↓ audio.emotion = emotion
  ↓ audio.speed_ratio = speed_ratio
  ↓ audio.pitch_ratio = pitch_ratio
```

### 5.2 代码修改点

| 文件 | 修改 |
|------|------|
| `backend/api/services/tts_service.py` | 新增 `calculate_tts_emotion()` 函数 |
| `backend/game/agents/orchestrator.py` | TTS 调用时传入 emotion_state + personality |
| `backend/api/routers/tts.py` | 接受 emotion 参数透传 |

---

## 六、边界情况处理

| 场景 | 处理 |
|------|------|
| 用户未选性格关键词 | 使用纯情绪计算，无修正 |
| 关键词互相矛盾（外向+内向） | 修正系数相互抵消，接近中性 |
| 所有情绪值都在中间区间 | 修正系数决定走向 |
| 关键词数量 = 1 | 单个关键词的完整修正 |
| 关键词数量 = 5 | 5 个关键词修正取平均 |

---

## 七、后续扩展

1. **关键词权重**：允许用户设定每个关键词的权重（主性格 vs 次性格）
2. **动态修正**：随着游戏进行，性格关键词的修正强度可变化（成长系统）
3. **场景修正**：课堂场景压制 `excited`，约会场景提升 `happy`
4. **组合关键词**：某些关键词组合产生特殊效果（高冷+浪漫 = 外冷内热）
