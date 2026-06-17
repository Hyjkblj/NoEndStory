"""PAD 空间计算（基于 ALMA 论文）

将 12 维情绪状态映射到 Pleasure-Arousal-Dominance 三维空间
"""
from .models import EmotionState


def compute_pad_vector(emotion: EmotionState) -> tuple[float, float, float]:
    """计算 PAD 向量

    Returns:
        (pleasure, arousal, dominance) 各范围 -1.0 ~ 1.0
    """
    # Pleasure（愉悦度）
    pleasure = (
        emotion.happiness * 0.4 +
        emotion.favorability * 0.3 +
        emotion.trust * 0.2 +
        emotion.confidence * 0.1
        - emotion.sadness * 0.4
        - emotion.hostility * 0.3
        - emotion.anxiety * 0.2
        - emotion.stress * 0.1
    ) / 100

    # Arousal（唤醒度）
    arousal = (
        emotion.happiness * 0.2 +
        emotion.hostility * 0.3 +
        emotion.stress * 0.2 +
        emotion.anxiety * 0.2 +
        emotion.initiative * 0.1
        - emotion.sadness * 0.3
        - (100 - emotion.confidence) * 0.2
    ) / 100

    # Dominance（支配度）
    dominance = (
        emotion.confidence * 0.3 +
        emotion.initiative * 0.3 +
        emotion.favorability * 0.2 +
        emotion.trust * 0.2
        - emotion.hostility * 0.2
        - emotion.anxiety * 0.3
        - emotion.stress * 0.2
        - emotion.caution * 0.3
    ) / 100

    return (
        max(-1.0, min(1.0, pleasure)),
        max(-1.0, min(1.0, arousal)),
        max(-1.0, min(1.0, dominance)),
    )


def classify_mood(pleasure: float, arousal: float, dominance: float) -> str:
    """PAD 空间 → 心境八分区（来自 ALMA 论文）"""
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
    """计算情感强度（PAD 向量到原点的距离）"""
    return (pleasure**2 + arousal**2 + dominance**2) ** 0.5
