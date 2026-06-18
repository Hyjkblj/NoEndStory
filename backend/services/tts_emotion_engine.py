"""TTS 情感计算引擎

将游戏中的 12 维情绪状态 + 角色性格关键词，映射为豆包 TTS API 的情感参数。
纯规则计算，无 LLM 调用，耗时 < 1ms。

流程：
  情绪状态（12维） → 基础情感评分 → 性格关键词修正 → 选择最高分情感 → TTS参数输出
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import os

from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# 性格关键词 → 情感修正系数表
# ============================================================

PERSONALITY_MODIFIERS: Dict[str, Dict[str, float]] = {
    # 外放型：放大积极情绪
    '外向':      {'excited': +15, 'happy': +10, 'angry': +5,  'sad': -5,  'fear': -10, 'coldness': -15},
    '热情':      {'excited': +20, 'happy': +15, 'angry': 0,   'sad': -5,  'fear': -10, 'coldness': -20},
    '阳光':      {'excited': +15, 'happy': +15, 'angry': -5,  'sad': -10, 'fear': -15, 'coldness': -20},
    '直率':      {'excited': +10, 'happy': +5,  'angry': +10, 'sad': -5,  'fear': -10, 'coldness': -5},

    # 内敛型：抑制情感表达
    '内向':      {'excited': -15, 'happy': -5,  'angry': -5,  'sad': +5,  'fear': +5,  'coldness': +10},
    '慢热':      {'excited': -15, 'happy': -10, 'angry': -5,  'sad': +5,  'fear': +5,  'coldness': +15},
    '独立':      {'excited': -10, 'happy': -5,  'angry': -5,  'sad': 0,   'fear': -5,  'coldness': +10},
    '谨慎':      {'excited': -10, 'happy': -5,  'angry': -10, 'sad': +5,  'fear': +10, 'coldness': +5},
    '细腻':      {'excited': -5,  'happy': +5,  'angry': -10, 'sad': +10, 'fear': +10, 'coldness': 0},

    # 冷感型：大幅抑制，偏向冷淡
    '冷静':      {'excited': -20, 'happy': -10, 'angry': -15, 'sad': -5,  'fear': -15, 'coldness': +20},
    '高冷':      {'excited': -25, 'happy': -15, 'angry': -10, 'sad': -10, 'fear': -20, 'coldness': +25},
    '理性':      {'excited': -15, 'happy': -5,  'angry': -10, 'sad': -10, 'fear': -10, 'coldness': +15},
    '成熟':      {'excited': -15, 'happy': -5,  'angry': -10, 'sad': -5,  'fear': -10, 'coldness': +15},
    '洒脱':      {'excited': -10, 'happy': +5,  'angry': -10, 'sad': -15, 'fear': -15, 'coldness': +10},

    # 情感型：增强柔和表达
    '感性':      {'excited': +10, 'happy': +15, 'angry': +5,  'sad': +15, 'fear': +5,  'coldness': -15},
    '温柔':      {'excited': 0,   'happy': +10, 'angry': -15, 'sad': +10, 'fear': 0,   'coldness': -15},
    '体贴':      {'excited': 0,   'happy': +10, 'angry': -10, 'sad': +10, 'fear': +5,  'coldness': -10},
    '共情力强':   {'excited': +5,  'happy': +10, 'angry': -5,  'sad': +15, 'fear': +10, 'coldness': -15},
    '浪漫':      {'excited': +15, 'happy': +15, 'angry': -10, 'sad': +10, 'fear': -5,  'coldness': -20},

    # 力量型：减少恐惧/悲伤
    '勇敢':      {'excited': +10, 'happy': +5,  'angry': +10, 'sad': -10, 'fear': -20, 'coldness': 0},
    '自信':      {'excited': +15, 'happy': +10, 'angry': +5,  'sad': -15, 'fear': -20, 'coldness': -5},
    '执着':      {'excited': +5,  'happy': +5,  'angry': +10, 'sad': +5,  'fear': -5,  'coldness': -5},
    '有主见':    {'excited': +5,  'happy': +5,  'angry': +10, 'sad': -10, 'fear': -15, 'coldness': +5},
    '行动力强':   {'excited': +10, 'happy': +5,  'angry': +5,  'sad': -5,  'fear': -10, 'coldness': -10},
    '有责任感':   {'excited': 0,   'happy': +5,  'angry': +5,  'sad': -5,  'fear': -5,  'coldness': +5},

    # 其他
    '幽默':      {'excited': +10, 'happy': +15, 'angry': -5,  'sad': -5,  'fear': -10, 'coldness': -10},
    '善良':      {'excited': +5,  'happy': +10, 'angry': -15, 'sad': +5,  'fear': 0,   'coldness': -10},
    '可靠':      {'excited': 0,   'happy': +5,  'angry': -5,  'sad': -5,  'fear': -5,  'coldness': +5},
    '单纯':      {'excited': +10, 'happy': +15, 'angry': -10, 'sad': +5,  'fear': +5,  'coldness': -15},
    '好奇心强':   {'excited': +10, 'happy': +10, 'angry': 0,   'sad': -5,  'fear': -5,  'coldness': -10},
}


# ============================================================
# TTS 情感 → 语速/音调映射
# ============================================================

TTS_EMOTION_PARAMS: Dict[str, Dict[str, float]] = {
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
        all_scores: 所有情感的最终得分（调试用）
    """
    emotion: str = "neutral"
    speed_ratio: float = 1.0
    pitch_ratio: float = 1.0
    volume_ratio: float = 1.0
    confidence: float = 0.0
    all_scores: Dict[str, float] = field(default_factory=dict)


# ============================================================
# Step 1: 情绪 → 基础情感评分
# ============================================================

def compute_base_emotion_scores(emotion_state) -> Dict[str, float]:
    """将 12 维情绪状态映射到 10 种 TTS 情感的基础分

    Args:
        emotion_state: EmotionState 实例，包含 12 个 float 字段

    Returns:
        {emotion_name: score} 字典，分数范围 0-100
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

    scores = {
        # 积极情感
        'happy':   happiness * 0.4 + fav * 0.3 + trust * 0.2 + initiative * 0.1,
        'excited': happiness * 0.3 + initiative * 0.3 + fav * 0.2 + confidence * 0.2,

        # 消极情感
        'sad':       sadness * 0.5 + (100 - happiness) * 0.2 + (100 - confidence) * 0.2 + (100 - fav) * 0.1,
        'angry':     hostility * 0.4 + stress * 0.3 + (100 - trust) * 0.2 + (100 - fav) * 0.1,
        'fear':      anxiety * 0.4 + stress * 0.3 + (100 - confidence) * 0.2 + (100 - initiative) * 0.1,
        'depressed': sadness * 0.4 + (100 - confidence) * 0.3 + (100 - happiness) * 0.2 + (100 - initiative) * 0.1,

        # 关系情感
        'hate':     hostility * 0.5 + (100 - trust) * 0.3 + (100 - fav) * 0.2,
        'coldness': (100 - fav) * 0.3 + (100 - trust) * 0.3 + (100 - happiness) * 0.2 + (100 - initiative) * 0.2,

        # 特殊情感
        'surprised': 0,  # 由外部事件触发，此处不做自动计算

        # 兜底
        'neutral': 30.0,
    }

    return scores


# ============================================================
# Step 2: 性格关键词修正
# ============================================================

def apply_personality_modifiers(
    base_scores: Dict[str, float],
    personality_keywords: List[str],
) -> Dict[str, float]:
    """应用性格修正系数（取所有关键词的平均值）

    Args:
        base_scores: Step 1 计算的基础分
        personality_keywords: 角色性格关键词列表

    Returns:
        修正后的分数
    """
    if not personality_keywords:
        return base_scores

    total_mods: Dict[str, float] = {}
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


# ============================================================
# Step 3: 选择最高分情感
# ============================================================

def select_best_emotion(scores: Dict[str, float]) -> str:
    """选择得分最高的情感

    Args:
        scores: 修正后的情感得分

    Returns:
        情感标签名
    """
    # 确保分数在合理范围
    for emotion in scores:
        scores[emotion] = max(0.0, min(100.0, scores[emotion]))

    return max(scores, key=scores.get)


# ============================================================
# Step 4: 边界条件处理
# ============================================================

def _apply_boundary_rules(
    scores: Dict[str, float],
    emotion_state,
) -> Dict[str, float]:
    """边界条件处理

    根据方案五的规则，处理特殊边界场景。
    """
    fav = getattr(emotion_state, 'favorability', 50)
    hostility = getattr(emotion_state, 'hostility', 0)
    happiness = getattr(emotion_state, 'happiness', 50)
    stress = getattr(emotion_state, 'stress', 0)
    anxiety = getattr(emotion_state, 'anxiety', 0)

    # 规则1: 所有值在中间区间 → 倾向 neutral
    all_fields = [
        getattr(emotion_state, attr, 50)
        for attr in ['favorability', 'trust', 'hostility', 'emotion',
                      'happiness', 'sadness', 'stress', 'anxiety',
                      'confidence', 'initiative']
    ]
    if all(40 <= v <= 60 for v in all_fields):
        scores['neutral'] += 10

    # 规则2: 好感度和敌意同时高 → 优先看敌意
    if fav >= 60 and hostility >= 50:
        scores['angry'] += 15
        scores['happy'] -= 10

    # 规则3: 压力高但焦虑低 → 愤怒而非恐惧
    if stress >= 60 and anxiety <= 30:
        scores['angry'] += 10
        scores['fear'] -= 5

    # 规则4: 快乐高但好感低 → 意外的开心
    if happiness >= 60 and fav <= 40:
        scores['surprised'] += 15
        scores['happy'] -= 5

    return scores


# ============================================================
# Step 5: 输出最终参数
# ============================================================

def calculate_tts_params(
    emotion_state,
    personality_keywords: Optional[List[str]] = None,
    confidence_threshold: float = 0.15,
) -> TTSParams:
    """完整的 TTS 参数计算

    Args:
        emotion_state: 12 维情绪状态（EmotionState 实例或兼容对象）
        personality_keywords: 角色性格关键词列表（最多 5 个）
        confidence_threshold: 置信度阈值，低于此值降级为 neutral

    Returns:
        TTSParams 包含 emotion, speed_ratio, pitch_ratio, volume_ratio, confidence, all_scores
    """
    if personality_keywords is None:
        personality_keywords = []

    # Step 1: 基础情感评分
    base_scores = compute_base_emotion_scores(emotion_state)

    # Step 2: 性格修正
    adjusted_scores = apply_personality_modifiers(base_scores, personality_keywords)

    # Step 3: 边界条件处理
    adjusted_scores = _apply_boundary_rules(adjusted_scores, emotion_state)

    # 确保分数在合理范围
    for k in adjusted_scores:
        adjusted_scores[k] = max(0.0, min(100.0, adjusted_scores[k]))

    # Step 4: 选择最高分情感
    best_emotion = select_best_emotion(adjusted_scores)

    # Step 5: 获取语速/音调
    params = TTS_EMOTION_PARAMS.get(best_emotion, TTS_EMOTION_PARAMS['neutral'])

    # 计算置信度
    total = sum(adjusted_scores.values())
    confidence = adjusted_scores[best_emotion] / total if total > 0 else 0.0

    # 低置信度降级
    if confidence < confidence_threshold:
        best_emotion = 'neutral'
        params = TTS_EMOTION_PARAMS['neutral']
        logger.debug(
            f"置信度过低 ({confidence:.3f} < {confidence_threshold})，降级为 neutral"
        )

    # 应用语速/音调范围限制
    from config import (
        TTS_SPEED_MIN, TTS_SPEED_MAX,
        TTS_PITCH_MIN, TTS_PITCH_MAX,
    )

    speed = max(TTS_SPEED_MIN, min(TTS_SPEED_MAX, params['speed_ratio']))
    pitch = max(TTS_PITCH_MIN, min(TTS_PITCH_MAX, params['pitch_ratio']))

    return TTSParams(
        emotion=best_emotion,
        speed_ratio=round(speed, 3),
        pitch_ratio=round(pitch, 3),
        volume_ratio=1.0,
        confidence=round(confidence, 4),
        all_scores=adjusted_scores,
    )


# ============================================================
# 便捷函数：从字典解析性格关键词
# ============================================================

def extract_personality_keywords(character_personality: Dict) -> List[str]:
    """从角色性格数据中提取关键词列表

    Args:
        character_personality: character_data JSON 中的 personality 字段
            例如 {"keywords": ["温柔", "害羞"], "description": "..."}

    Returns:
        关键词列表
    """
    if not character_personality:
        return []

    keywords = character_personality.get("keywords", [])
    if isinstance(keywords, list):
        return [k for k in keywords if isinstance(k, str)]

    return []
