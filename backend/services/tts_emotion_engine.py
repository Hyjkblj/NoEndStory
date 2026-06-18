"""TTS 情感计算引擎（基于 ALMA 论文 PAD 空间）

将游戏中的 12 维情绪状态 + 角色性格关键词，映射为豆包 TTS API 的情感参数。
纯规则计算，无 LLM 调用，耗时 < 1ms。

理论基础：
  - ALMA 论文：情绪 → PAD（Pleasure-Arousal-Dominance）三维空间 → 心境八分区
  - 论文 2：情绪→语音韵律映射，个体差异 > 文化差异 > 全局映射

流程：
  情绪状态（12维） → PAD 向量 → 心境八分区 → 情感选择 → 语速/音调动态计算 → TTS参数输出
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import os

from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# ALMA 论文：OCC 情绪 → PAD 映射表
# ============================================================

EMOTION_PAD_MAP: Dict[str, Tuple[float, float, float]] = {
    # (Pleasure, Arousal, Dominance)
    'joy':        (0.4, 0.2, 0.1),
    'happy':      (0.4, 0.2, 0.1),    # 别名
    'anger':      (-0.51, 0.59, 0.25),
    'angry':      (-0.51, 0.59, 0.25), # 别名
    'fear':       (-0.64, 0.60, -0.43),
    'sadness':    (-0.4, -0.2, -0.5),
    'sad':        (-0.4, -0.2, -0.5),  # 别名
    'love':       (0.3, 0.1, 0.2),
    'hate':       (-0.6, 0.6, 0.3),
    'surprise':   (0.2, 0.5, -0.1),
    'surprised':  (0.2, 0.5, -0.1),   # 别名
    'admiration': (0.5, 0.3, -0.2),
    'hope':       (0.2, 0.2, -0.1),
    'gratitude':  (0.4, 0.2, -0.3),
    'pride':      (0.4, 0.3, 0.3),
    'shame':      (-0.4, -0.2, -0.6),
    'contempt':   (-0.3, 0.1, 0.4),
    'disgust':    (-0.4, 0.2, 0.1),
}


# ============================================================
# 心境八分区 → TTS 情感映射（来自 ALMA 论文）
# ============================================================

MOOD_TO_TTS_EMOTION: Dict[str, str] = {
    '+P+A+D': 'excited',    # 兴奋 → 激动
    '+P+A-D': 'happy',      # 依赖 → 开心（偏柔和）
    '+P-A+D': 'happy',      # 放松 → 开心（偏平静）
    '+P-A-D': 'neutral',    # 顺从 → 中性
    '-P+A+D': 'angry',      # 敌意 → 生气
    '-P+A-D': 'fear',       # 焦虑 → 恐惧
    '-P-A+D': 'coldness',   # 轻蔑 → 冷漠
    '-P-A-D': 'depressed',  # 无聊 → 沮丧
}


# ============================================================
# 性格关键词 → PAD 修正系数（替代旧的离散修正表）
# ============================================================

PERSONALITY_PAD_MODIFIERS: Dict[str, Tuple[float, float, float]] = {
    # (P修正, A修正, D修正)
    # 外放型：提高 P 和 A
    '外向':      (0.08, 0.10, 0.05),
    '热情':      (0.12, 0.12, 0.03),
    '阳光':      (0.10, 0.08, 0.05),
    '直率':      (0.05, 0.08, 0.08),

    # 内敛型：降低 A 和 D
    '内向':      (-0.05, -0.10, -0.05),
    '慢热':      (-0.08, -0.12, -0.03),
    '独立':      (0.00, -0.05, 0.08),
    '谨慎':      (-0.03, -0.08, -0.05),
    '细腻':      (0.03, -0.05, -0.05),

    # 冷感型：降低 P 和 A，提高 D
    '冷静':      (-0.05, -0.10, 0.10),
    '高冷':      (-0.10, -0.15, 0.12),
    '理性':      (-0.05, -0.08, 0.10),
    '成熟':      (-0.03, -0.08, 0.08),
    '洒脱':      (0.03, -0.08, 0.05),

    # 情感型：提高 P，变化 A
    '感性':      (0.08, 0.05, -0.03),
    '温柔':      (0.08, -0.05, -0.05),
    '体贴':      (0.06, -0.03, -0.03),
    '共情力强':   (0.06, 0.05, -0.05),
    '浪漫':      (0.10, 0.05, -0.03),

    # 力量型：提高 D，降低负向 A
    '勇敢':      (0.05, 0.05, 0.12),
    '自信':      (0.08, 0.05, 0.15),
    '执着':      (0.03, 0.05, 0.08),
    '有主见':    (0.03, 0.03, 0.12),
    '行动力强':   (0.05, 0.08, 0.08),
    '有责任感':   (0.03, 0.00, 0.10),

    # 其他
    '幽默':      (0.08, 0.05, 0.05),
    '善良':      (0.08, -0.03, -0.05),
    '可靠':      (0.03, -0.03, 0.05),
    '单纯':      (0.08, 0.05, -0.08),
    '好奇心强':   (0.05, 0.08, 0.00),
}


# ============================================================
# PAD 空间 → 语速/音调动态计算
# ============================================================

def compute_speed_from_pad(p: float, a: float, d: float) -> float:
    """根据 PAD 向量动态计算语速

    基于论文 2 的发现：
    - Arousal 高 → 语速快（愤怒、恐惧、激动）
    - Arousal 低 → 语速慢（悲伤、冷漠）
    - Dominance 高 → 语速适中偏快（自信）
    """
    base_speed = 1.0
    # Arousal 贡献最大（范围 -1~1 → -0.15~+0.15）
    speed = base_speed + a * 0.15
    # Dominance 微调（范围 -1~1 → -0.03~+0.03）
    speed += d * 0.03
    # Pleasure 微调（范围 -1~1 → -0.02~+0.02）
    speed += p * 0.02

    return max(0.7, min(1.3, speed))


def compute_pitch_from_pad(p: float, a: float, d: float) -> float:
    """根据 PAD 向量动态计算音调

    基于论文 2 的发现：
    - Arousal 高 → 音调高（恐惧、惊讶）
    - Arousal 低 → 音调低（悲伤、冷漠）
    - Pleasure 高 → 音调微高（开心）
    - Pleasure 低 → 音调微低（悲伤）
    """
    base_pitch = 1.0
    # Arousal 贡献最大（范围 -1~1 → -0.08~+0.08）
    pitch = base_pitch + a * 0.08
    # Pleasure 微调（范围 -1~1 → -0.03~+0.03）
    pitch += p * 0.03
    # Dominance 微调（范围 -1~1 → -0.02~+0.02）
    pitch += d * 0.02

    return max(0.88, min(1.12, pitch))


# ============================================================
# 输出数据结构
# ============================================================

@dataclass
class TTSParams:
    """最终 TTS 参数

    Attributes:
        emotion: 情感标签（happy/sad/angry/surprised/fear/hate/excited/coldness/neutral/depressed）
        speed_ratio: 语速 0.5-2.0
        pitch_ratio: 音调 0.5-2.0
        volume_ratio: 音量 0.1-2.0（默认固定 1.0）
        confidence: 情感评分置信度（0-1，小于阈值则降级为 neutral）
        pad_vector: PAD 向量 (P, A, D) 范围 -1.0~1.0
        mood_octant: 心境八分区名称
        all_scores: 所有情感的最终得分（调试用）
    """
    emotion: str = "neutral"
    speed_ratio: float = 1.0
    pitch_ratio: float = 1.0
    volume_ratio: float = 1.0
    confidence: float = 0.0
    pad_vector: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mood_octant: str = "neutral"
    all_scores: Dict[str, float] = field(default_factory=dict)


# ============================================================
# Step 1: 12 维情绪 → PAD 向量
# ============================================================

def compute_pad_from_emotion(emotion_state) -> Tuple[float, float, float]:
    """将 12 维情绪状态映射到 PAD 空间（基于 ALMA 论文）

    关键设计：极端值（>70 或 <30）使用非线性权重，让极端情绪不会被中和。

    Args:
        emotion_state: EmotionState 实例，包含 12 个 float 字段

    Returns:
        (pleasure, arousal, dominance) 各范围 -1.0 ~ 1.0
    """
    fav = getattr(emotion_state, 'favorability', 50)
    trust = getattr(emotion_state, 'trust', 50)
    hostility = getattr(emotion_state, 'hostility', 0)
    happiness = getattr(emotion_state, 'happiness', 50)
    sadness = getattr(emotion_state, 'sadness', 0)
    stress = getattr(emotion_state, 'stress', 0)
    anxiety = getattr(emotion_state, 'anxiety', 0)
    confidence = getattr(emotion_state, 'confidence', 50)
    initiative = getattr(emotion_state, 'initiative', 50)
    caution = getattr(emotion_state, 'caution', 50)

    def extreme_weight(val: float, threshold_high: float = 70, threshold_low: float = 30) -> float:
        """极端值非线性加权：>70 或 <30 的值权重翻倍"""
        normalized = val / 100
        if val > threshold_high:
            return normalized * 1.5  # 高值放大
        elif val < threshold_low:
            return normalized * 0.5  # 低值缩小（让负面贡献更明显）
        return normalized

    # Pleasure（愉悦度）
    # 正面：happiness, fav, trust, confidence
    # 负面：sadness, hostility, anxiety, stress
    pos_p = (
        extreme_weight(happiness) * 0.4 +
        extreme_weight(fav) * 0.3 +
        extreme_weight(trust) * 0.2 +
        extreme_weight(confidence) * 0.1
    )
    neg_p = (
        extreme_weight(sadness) * 0.4 +
        extreme_weight(hostility) * 0.3 +
        extreme_weight(anxiety) * 0.2 +
        extreme_weight(stress) * 0.1
    )
    pleasure = pos_p - neg_p

    # Arousal（唤醒度）
    # 高能量：happiness, hostility, stress, anxiety, initiative
    # 低能量：sadness, low confidence
    arousal = (
        (extreme_weight(happiness) * 0.2 +
         extreme_weight(hostility) * 0.3 +
         extreme_weight(stress) * 0.2 +
         extreme_weight(anxiety) * 0.2 +
         extreme_weight(initiative) * 0.1)
        - (extreme_weight(sadness) * 0.3 +
           (1 - extreme_weight(confidence)) * 0.2)
    )

    # Dominance（支配度）
    # 高支配：confidence, initiative, fav, trust
    # 低支配：hostility, anxiety, stress, caution
    dominance = (
        (extreme_weight(confidence) * 0.3 +
         extreme_weight(initiative) * 0.3 +
         extreme_weight(fav) * 0.2 +
         extreme_weight(trust) * 0.2)
        - (extreme_weight(hostility) * 0.2 +
           extreme_weight(anxiety) * 0.3 +
           extreme_weight(stress) * 0.2 +
           extreme_weight(caution) * 0.3)
    )

    return (
        max(-1.0, min(1.0, pleasure)),
        max(-1.0, min(1.0, arousal)),
        max(-1.0, min(1.0, dominance)),
    )


# ============================================================
# Step 2: PAD 向量 → 心境八分区
# ============================================================

def classify_mood(p: float, a: float, d: float) -> str:
    """PAD 空间 → 心境八分区（来自 ALMA 论文）

    心境八分区：
        +P+A+D 兴奋(Exuberant)    -P-A-D 无聊(Bored)
        +P+A-D 依赖(Dependent)    -P-A+D 轻蔑(Disdainful)
        +P-A+D 放松(Relaxed)      -P+A-D 焦虑(Anxious)
        +P-A-D 顺从(Docile)       -P+A+D 敌意(Hostile)
    """
    p_sign = '+P' if p >= 0 else '-P'
    a_sign = 'A' if a >= 0 else '-A'
    d_sign = 'D' if d >= 0 else '-D'
    return f'{p_sign}{a_sign}{d_sign}'


# ============================================================
# Step 3: 性格关键词 → PAD 修正
# ============================================================

def apply_personality_pad_modifiers(
    p: float, a: float, d: float,
    personality_keywords: List[str],
) -> Tuple[float, float, float]:
    """应用性格修正到 PAD 向量（基于论文 2 的个体差异理论）

    Args:
        p, a, d: 原始 PAD 值
        personality_keywords: 角色性格关键词列表

    Returns:
        修正后的 (p, a, d)
    """
    if not personality_keywords:
        return p, a, d

    total_dp, total_da, total_dd = 0.0, 0.0, 0.0
    count = 0

    for keyword in personality_keywords:
        if keyword in PERSONALITY_PAD_MODIFIERS:
            dp, da, dd = PERSONALITY_PAD_MODIFIERS[keyword]
            total_dp += dp
            total_da += da
            total_dd += dd
            count += 1

    if count == 0:
        return p, a, d

    # 取平均值
    avg_dp = total_dp / count
    avg_da = total_da / count
    avg_dd = total_dd / count

    return (
        max(-1.0, min(1.0, p + avg_dp)),
        max(-1.0, min(1.0, a + avg_da)),
        max(-1.0, min(1.0, d + avg_dd)),
    )


# ============================================================
# Step 4: PAD 向量 + 心境 → TTS 情感选择
# ============================================================

def select_tts_emotion(
    p: float, a: float, d: float,
    mood: str,
    intensity: float,
    emotion_state=None,  # 可选：原始情绪状态，用于极端值检测
) -> Tuple[str, float]:
    """根据 PAD 向量和心境选择 TTS 情感

    三层判定：
    1. 极端值直接映射（单维度 > 70，绕过 PAD）
    2. PAD 值直接判断
    3. 心境八分区映射（兜底）

    Args:
        p, a, d: PAD 值
        mood: 心境八分区
        intensity: 情感强度
        emotion_state: 原始情绪状态（可选）

    Returns:
        (emotion_label, confidence)
    """
    # ===== 第 1 层：极端值直接映射 =====
    if emotion_state is not None:
        hostility = getattr(emotion_state, 'hostility', 0)
        sadness = getattr(emotion_state, 'sadness', 0)
        anxiety = getattr(emotion_state, 'anxiety', 0)
        happiness = getattr(emotion_state, 'happiness', 0)
        stress = getattr(emotion_state, 'stress', 0)
        fav = getattr(emotion_state, 'favorability', 50)
        trust = getattr(emotion_state, 'trust', 50)

        # 高敌意 → angry
        if hostility >= 65:
            return 'angry', min(1.0, hostility / 80)

        # 高悲伤 + 低快乐 → depressed
        if sadness >= 65 and happiness <= 30:
            return 'depressed', min(1.0, sadness / 80)

        # 高悲伤 → sad
        if sadness >= 60:
            return 'sad', min(1.0, sadness / 80)

        # 高焦虑 + 高压力 → fear
        if anxiety >= 60 and stress >= 50:
            return 'fear', min(1.0, (anxiety + stress) / 160)

        # 高焦虑 → fear
        if anxiety >= 65:
            return 'fear', min(1.0, anxiety / 80)

        # 高快乐 + 高好感 + 高信任 → happy
        if happiness >= 70 and fav >= 60 and trust >= 50:
            return 'happy', min(1.0, happiness / 80)

        # 高快乐 + 高主动 → excited
        if happiness >= 70 and getattr(emotion_state, 'initiative', 50) >= 60:
            return 'excited', min(1.0, happiness / 80)

        # 低好感 + 低信任 → coldness
        if fav <= 25 and trust <= 25:
            return 'coldness', min(1.0, (100 - fav - trust) / 100)

        # 低好感 + 高敌意 → hate
        if fav <= 35 and hostility >= 40:
            return 'hate', min(1.0, hostility / 80)

    # ===== 第 2 层：PAD 值判断 =====
    P_HIGH, P_LOW = 0.15, -0.15
    A_HIGH, A_LOW = 0.15, -0.15

    if p > P_HIGH and a > A_HIGH:
        return 'excited', min(1.0, intensity / 0.5)
    if p > P_HIGH and a <= A_HIGH:
        return 'happy', min(1.0, intensity / 0.5)
    if p < P_LOW and a > A_HIGH and d > 0:
        return 'angry', min(1.0, intensity / 0.5)
    if p < P_LOW and a > A_HIGH and d <= 0:
        return 'fear', min(1.0, intensity / 0.5)
    if p < P_LOW and a <= A_LOW and d <= 0:
        return 'depressed', min(1.0, intensity / 0.5)
    if p < P_LOW and a <= A_LOW and d > 0:
        return 'coldness', min(1.0, intensity / 0.5)

    # ===== 第 3 层：心境八分区兜底 =====
    mood_emotion = MOOD_TO_TTS_EMOTION.get(mood, 'neutral')
    confidence = min(1.0, intensity / 0.5)

    return mood_emotion, confidence


# ============================================================
# Step 5: 完整计算函数
# ============================================================

def calculate_tts_params(
    emotion_state,
    personality_keywords: Optional[List[str]] = None,
    confidence_threshold: float = 0.15,
) -> TTSParams:
    """完整的 TTS 参数计算（基于 ALMA PAD 空间）

    Args:
        emotion_state: 12 维情绪状态（EmotionState 实例或兼容对象）
        personality_keywords: 角色性格关键词列表（最多 5 个）
        confidence_threshold: 置信度阈值，低于此值降级为 neutral

    Returns:
        TTSParams 包含 emotion, speed_ratio, pitch_ratio, pad_vector, mood_octant 等
    """
    if personality_keywords is None:
        personality_keywords = []

    # Step 1: 12 维情绪 → PAD 向量
    p, a, d = compute_pad_from_emotion(emotion_state)

    # Step 2: PAD 向量 → 心境八分区
    mood = classify_mood(p, a, d)

    # Step 3: 性格修正（基于论文 2 的个体差异理论）
    p, a, d = apply_personality_pad_modifiers(p, a, d, personality_keywords)

    # 修正后重新计算心境
    mood = classify_mood(p, a, d)

    # 计算情感强度
    intensity = (p**2 + a**2 + d**2) ** 0.5

    # Step 4: 选择 TTS 情感
    emotion, confidence = select_tts_emotion(p, a, d, mood, intensity, emotion_state)

    # Step 5: 动态计算语速/音调
    speed = compute_speed_from_pad(p, a, d)
    pitch = compute_pitch_from_pad(p, a, d)

    # 低置信度降级
    if confidence < confidence_threshold:
        emotion = 'neutral'
        speed = 1.0
        pitch = 1.0
        logger.debug(f"置信度过低 ({confidence:.3f} < {confidence_threshold})，降级为 neutral")

    # 应用语速/音调范围限制
    try:
        from config import TTS_SPEED_MIN, TTS_SPEED_MAX, TTS_PITCH_MIN, TTS_PITCH_MAX
        speed = max(TTS_SPEED_MIN, min(TTS_SPEED_MAX, speed))
        pitch = max(TTS_PITCH_MIN, min(TTS_PITCH_MAX, pitch))
    except ImportError:
        speed = max(0.7, min(1.3, speed))
        pitch = max(0.88, min(1.12, pitch))

    return TTSParams(
        emotion=emotion,
        speed_ratio=round(speed, 3),
        pitch_ratio=round(pitch, 3),
        volume_ratio=1.0,
        confidence=round(confidence, 4),
        pad_vector=(round(p, 3), round(a, 3), round(d, 3)),
        mood_octant=mood,
    )


# ============================================================
# 便捷函数
# ============================================================

def extract_personality_keywords(character_personality: Dict) -> List[str]:
    """从角色性格数据中提取关键词列表"""
    if not character_personality:
        return []
    keywords = character_personality.get("keywords", [])
    if isinstance(keywords, list):
        return [k for k in keywords if isinstance(k, str)]
    return []
