"""ScriptEngine V2 数据结构"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Option:
    """玩家选项"""
    id: int
    text: str
    direction: str  # positive / neutral / negative
    state_changes: Dict[str, float] = field(default_factory=dict)


@dataclass
class RoundOutput:
    """ScriptEngine 单轮输出"""
    scene: str
    character_dialogue: str
    player_options: List[Option]
    emotion_changes: Dict[str, float]
    event_advance: bool
    event_ended: bool
    phase: str
    is_game_finished: bool = False
    ending_type: Optional[str] = None
    event_type: Optional[str] = None
    event_description: Optional[str] = None
