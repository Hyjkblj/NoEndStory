"""30分钟叙事节拍表"""
from .state import NarrativeBeat, SessionPhase

# 起承转合四段，总计约30分钟
# 每轮对话约1-2分钟
NARRATIVE_BEATS = [
    NarrativeBeat(
        name="开场相识",
        phase=SessionPhase.OPENING,
        start_minute=0.0,
        end_minute=5.0,
        min_rounds=3,
        max_rounds=5,
        emotion_target="neutral_warm",
        event_pool=["first_meeting", "casual_chat", "mutual_introduction"],
    ),
    NarrativeBeat(
        name="关系建立",
        phase=SessionPhase.RISING,
        start_minute=5.0,
        end_minute=13.0,
        min_rounds=5,
        max_rounds=8,
        emotion_target="growing_close",
        event_pool=["shared_activity", "small_conflict", "personal_revelation", "help_moment"],
    ),
    NarrativeBeat(
        name="冲突爆发",
        phase=SessionPhase.CLIMAX,
        start_minute=13.0,
        end_minute=23.0,
        min_rounds=5,
        max_rounds=8,
        emotion_target="intense",
        event_pool=["major_conflict", "critical_choice", "emotional_confession", "betrayal"],
    ),
    NarrativeBeat(
        name="冲突化解",
        phase=SessionPhase.RESOLUTION,
        start_minute=23.0,
        end_minute=30.0,
        min_rounds=3,
        max_rounds=5,
        emotion_target="resolution",
        event_pool=["reconciliation", "final_choice", "departure", "promise"],
    ),
]


def get_current_beat(elapsed_minutes: float):
    """根据已过时间返回当前叙事节拍"""
    for beat in NARRATIVE_BEATS:
        if beat.start_minute <= elapsed_minutes < beat.end_minute:
            return beat
    return NARRATIVE_BEATS[-1]  # 兜底


def get_next_beat(elapsed_minutes: float):
    """获取下一个叙事节拍"""
    beats = NARRATIVE_BEATS
    for i, beat in enumerate(beats):
        if beat.start_minute <= elapsed_minutes < beat.end_minute:
            return beats[i + 1] if i + 1 < len(beats) else None
    return None
