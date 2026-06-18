"""AgentState — 全局共享状态对象"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class SessionPhase(Enum):
    """游戏阶段"""
    INIT = "init"           # 初始化
    OPENING = "opening"     # 开场事件
    RISING = "rising"       # 发展期（承）
    CLIMAX = "climax"       # 高潮期（转）
    RESOLUTION = "resolution"  # 结局期（合）
    ENDING = "ending"       # 结局
    FINISHED = "finished"   # 已结束


@dataclass
class NarrativeBeat:
    """叙事节拍定义"""
    name: str                                # 节拍名称
    phase: SessionPhase                      # 所属阶段
    start_minute: float                      # 开始时间（分钟）
    end_minute: float                        # 结束时间（分钟）
    min_rounds: int = 3                      # 最少对话轮数
    max_rounds: int = 8                      # 最多对话轮数
    emotion_target: str = "neutral"          # 目标情绪基调
    event_pool: List[str] = field(default_factory=list)  # 推荐事件类型


@dataclass
class WorldState:
    """世界状态"""
    current_scene: str = "classroom"         # 当前场景ID
    current_time: str = "morning"            # 当前时间（morning/afternoon/evening/night）
    weather: str = "clear"                   # 天气
    elapsed_minutes: float = 0.0             # 已过游戏时间
    time_of_day_progress: float = 0.0        # 日夜推进进度


@dataclass
class EmotionState:
    """12维情绪状态"""
    favorability: float = 50.0
    trust: float = 50.0
    hostility: float = 0.0
    dependence: float = 50.0
    emotion: float = 50.0
    stress: float = 0.0
    anxiety: float = 0.0
    happiness: float = 50.0
    sadness: float = 0.0
    confidence: float = 50.0
    initiative: float = 50.0
    caution: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "favorability": self.favorability,
            "trust": self.trust,
            "hostility": self.hostility,
            "dependence": self.dependence,
            "emotion": self.emotion,
            "stress": self.stress,
            "anxiety": self.anxiety,
            "happiness": self.happiness,
            "sadness": self.sadness,
            "confidence": self.confidence,
            "initiative": self.initiative,
            "caution": self.caution,
        }

    def apply_changes(self, changes: Dict[str, float]) -> None:
        """应用状态变化，自动 clamp 到 0-100"""
        for key, delta in changes.items():
            if hasattr(self, key):
                current = getattr(self, key)
                setattr(self, key, max(0.0, min(100.0, current + delta)))

    def pad_vector(self) -> Dict[str, float]:
        """PAD 三维映射：Pleasure(愉悦), Arousal(唤醒), Dominance(支配)"""
        pleasure = (self.happiness - self.sadness + self.favorability / 2) / 2 + 50
        arousal = (self.emotion + self.stress + self.anxiety) / 3
        dominance = (self.confidence + self.initiative - self.caution) / 2 + 50
        return {
            "pleasure": max(0.0, min(100.0, pleasure)),
            "arousal": max(0.0, min(100.0, arousal)),
            "dominance": max(0.0, min(100.0, dominance)),
        }


@dataclass
class AgentState:
    """全局 Agent 状态 — 所有 Agent 共享"""
    # 基础标识
    thread_id: str = ""
    character_id: int = 0
    character_name: str = ""
    character_personality: Dict[str, Any] = field(default_factory=dict)

    # 叙事状态
    phase: SessionPhase = SessionPhase.INIT
    current_beat: Optional[NarrativeBeat] = None
    round_count: int = 0
    total_rounds: int = 0

    # 世界状态
    world: WorldState = field(default_factory=WorldState)

    # 情绪状态
    emotion: EmotionState = field(default_factory=EmotionState)

    # 对话历史
    dialogue_history: List[Dict[str, Any]] = field(default_factory=list)
    pending_event: Optional[Dict[str, Any]] = None
    last_character_dialogue: str = ""
    last_player_input: str = ""

    # 事件追踪
    event_history: List[Dict[str, Any]] = field(default_factory=list)
    used_event_ids: set = field(default_factory=set)

    # 一致性校验结果
    consistency_checks: List[str] = field(default_factory=list)

    # 输出
    output_dialogue: str = ""
    output_options: List[Dict[str, Any]] = field(default_factory=list)
    output_scene: str = ""
    output_scene_image_url: str = ""
    output_audio_url: str = ""
    output_audio_duration: float = 0.0
    output_emotion_changes: Dict[str, float] = field(default_factory=dict)
    output_tts_params: Any = None  # TTSParams from tts_emotion_engine

    def advance_round(self) -> None:
        self.round_count += 1
        self.total_rounds += 1

    def add_to_history(self, role: str, content: str, metadata: Dict = None) -> None:
        self.dialogue_history.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
        })
