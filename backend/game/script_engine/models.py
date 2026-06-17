"""动态剧本系统的数据结构定义"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EmotionState:
    """12 维情绪状态"""
    favorability: float = 50.0  # 好感度
    trust: float = 50.0         # 信任度
    hostility: float = 0.0      # 敌意值
    emotion: float = 50.0       # 整体情绪值
    stress: float = 20.0        # 压力值
    anxiety: float = 10.0       # 焦虑值
    happiness: float = 50.0     # 快乐值
    sadness: float = 10.0       # 悲伤值
    confidence: float = 50.0    # 自信值
    initiative: float = 50.0    # 主动性
    caution: float = 50.0       # 谨慎度
    emotion_target: str = "neutral"

    def copy(self) -> EmotionState:
        return EmotionState(**self.__dict__)

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> EmotionState:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PlayerOption:
    """玩家选项"""
    id: int
    text: str
    state_changes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text}


@dataclass
class KeyBeat:
    """关键节拍：剧情必须推进到的节点"""
    beat_index: int
    trigger_round: int
    narrative_content: str
    emotion_target_range: dict = field(default_factory=dict)
    option_directions: list[str] = field(default_factory=lambda: ["积极回应", "保持中性", "消极回应"])
    scene_mood: str = "自然"


@dataclass
class OpeningEvent:
    """开场事件（从场景事件池随机选取）"""
    title: str
    description: str
    scene: str
    mood: str = "自然"
    option_directions: list[str] = field(default_factory=lambda: ["积极回应", "保持中性", "消极回应"])


@dataclass
class EventDraft:
    """事件草案"""
    draft_id: str
    title: str
    scene: str
    narrative_beat: str  # opening / rising / climax / resolution
    brief_description: str
    key_beats: list[KeyBeat] = field(default_factory=list)
    emotion_direction: dict = field(default_factory=dict)
    estimated_rounds: int = 3
    detail_level: str = "brief"  # full / brief
    opening_event: Optional[OpeningEvent] = None


@dataclass
class EventSummary:
    """已完成事件的摘要"""
    event_id: str
    title: str
    scene: str
    rounds_played: int
    key_events: str
    emotion_changes: dict = field(default_factory=dict)
    player_choices_summary: str = ""


@dataclass
class AnchorPoint:
    """叙事锚点"""
    anchor_id: int
    target_event_range: tuple[int, int]
    narrative_goal: str
    emotion_milestone: dict = field(default_factory=dict)
    is_achieved: bool = False


@dataclass
class NarrativeAnchor:
    """叙事锚点集合"""
    theme: str
    anchor_points: list[AnchorPoint] = field(default_factory=list)
    total_events: int = 5
    emotional_arc: str = "低开高走"


@dataclass
class GameState:
    """游戏全局状态"""
    thread_id: str
    character_id: int
    character_name: str
    character_personality: list[str]
    scene_id: str
    emotion: EmotionState = field(default_factory=EmotionState)

    # 剧本状态
    current_event: Optional[EventDraft] = None
    current_beat_index: int = 0
    current_event_rounds: int = 0
    dialogue_history: list = field(default_factory=list)
    current_options: list[PlayerOption] = field(default_factory=list)

    # 草案队列
    draft_queue: list[EventDraft] = field(default_factory=list)
    completed_events: list[EventSummary] = field(default_factory=list)
    narrative_anchor: Optional[NarrativeAnchor] = None

    # 进度追踪
    total_rounds: int = 0
    total_events: int = 0

    # 结局状态
    is_finished: bool = False
    ending_type: Optional[str] = None

    def to_dict(self) -> dict:
        """序列化（用于持久化）"""
        return {
            "thread_id": self.thread_id,
            "character_id": self.character_id,
            "character_name": self.character_name,
            "character_personality": self.character_personality,
            "scene_id": self.scene_id,
            "emotion": self.emotion.to_dict(),
            "total_rounds": self.total_rounds,
            "total_events": self.total_events,
            "is_finished": self.is_finished,
            "ending_type": self.ending_type,
            "current_beat_index": self.current_beat_index,
            "current_event_rounds": self.current_event_rounds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GameState:
        emotion_data = data.pop("emotion", {})
        state = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        state.emotion = EmotionState.from_dict(emotion_data)
        return state
