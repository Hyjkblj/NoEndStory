"""PAD 空间计算（基于 ALMA 论文）

将 12 维情绪状态映射到 Pleasure-Arousal-Dominance 三维空间。
与 TTS 情感引擎使用相同的计算逻辑，保证一致性。

理论来源：
  - ALMA 论文：OCC 情绪 → PAD 映射
  - 论文 2：情绪→语音韵律映射，个体差异理论
"""
from typing import Tuple
from .models import EmotionState


def compute_pad_vector(emotion: EmotionState) -> Tuple[float, float, float]:
    """计算 PAD 向量

    计算方式：正面贡献 - 负面贡献，结果自然在 -1~1 范围

    Args:
        emotion: 12 维情绪状态

    Returns:
        (pleasure, arousal, dominance) 各范围 -1.0 ~ 1.0
    """
    fav = emotion.favorability / 100
    trust = emotion.trust / 100
    hostility = emotion.hostility / 100
    happiness = emotion.happiness / 100
    sadness = emotion.sadness / 100
    stress = emotion.stress / 100
    anxiety = emotion.anxiety / 100
    confidence = emotion.confidence / 100
    initiative = emotion.initiative / 100
    caution = emotion.caution / 100

    # Pleasure（愉悦度）：正面情绪 - 负面情绪
    pleasure = (
        (happiness * 0.4 + fav * 0.3 + trust * 0.2 + confidence * 0.1)
        - (sadness * 0.4 + hostility * 0.3 + anxiety * 0.2 + stress * 0.1)
    )

    # Arousal（唤醒度）：高能量情绪 - 低能量情绪
    arousal = (
        (happiness * 0.2 + hostility * 0.3 + stress * 0.2 + anxiety * 0.2 + initiative * 0.1)
        - (sadness * 0.3 + (1 - confidence) * 0.2)
    )

    # Dominance（支配度）：控制感 - 被控制感
    dominance = (
        (confidence * 0.3 + initiative * 0.3 + fav * 0.2 + trust * 0.2)
        - (hostility * 0.2 + anxiety * 0.3 + stress * 0.2 + caution * 0.3)
    )

    return (
        max(-1.0, min(1.0, pleasure)),
        max(-1.0, min(1.0, arousal)),
        max(-1.0, min(1.0, dominance)),
    )


def classify_mood(pleasure: float, arousal: float, dominance: float) -> str:
    """PAD 空间 → 心境八分区（来自 ALMA 论文）

    心境八分区：
        +P+A+D 兴奋(Exuberant)    -P-A-D 无聊(Bored)
        +P+A-D 依赖(Dependent)    -P-A+D 轻蔑(Disdainful)
        +P-A+D 放松(Relaxed)      -P+A-D 焦虑(Anxious)
        +P-A-D 顺从(Docile)       -P+A+D 敌意(Hostile)
    """
    p = '+P' if pleasure >= 0 else '-P'
    a = 'A' if arousal >= 0 else '-A'
    d = 'D' if dominance >= 0 else '-D'

    mood_map = {
        '+P+A+D': 'exuberant',    # 兴奋
        '+P+A-D': 'dependent',    # 依赖
        '+P-A+D': 'relaxed',      # 放松
        '+P-A-D': 'docile',       # 顺从
        '-P+A+D': 'hostile',      # 敌意
        '-P+A-D': 'anxious',      # 焦虑
        '-P-A+D': 'disdainful',   # 轻蔑
        '-P-A-D': 'bored',        # 无聊
    }

    return mood_map.get(f'{p}{a}{d}', 'neutral')


def compute_intensity(pleasure: float, arousal: float, dominance: float) -> float:
    """计算情感强度（PAD 向量到原点的距离）

    Returns:
        强度值 0~√3 ≈ 0~1.732
    """
    return (pleasure**2 + arousal**2 + dominance**2) ** 0.5


# ALMA 论文：OCC 情绪 → PAD 映射表
EMOTION_PAD_MAP = {
    'joy':        (0.4, 0.2, 0.1),
    'anger':      (-0.51, 0.59, 0.25),
    'fear':       (-0.64, 0.60, -0.43),
    'sadness':    (-0.4, -0.2, -0.5),
    'love':       (0.3, 0.1, 0.2),
    'hate':       (-0.6, 0.6, 0.3),
    'surprise':   (0.2, 0.5, -0.1),
    'admiration': (0.5, 0.3, -0.2),
    'hope':       (0.2, 0.2, -0.1),
    'gratitude':  (0.4, 0.2, -0.3),
    'pride':      (0.4, 0.3, 0.3),
    'shame':      (-0.4, -0.2, -0.6),
    'contempt':   (-0.3, 0.1, 0.4),
    'disgust':    (-0.4, 0.2, 0.1),
}
