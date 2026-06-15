"""NOS 简化版 Agent 引擎（7 Agent + 状态机）

架构:
    Director Agent ──┬── Emotion Agent
                     ├── World Simulator
                     ├── Event Agent
                     ├── Future Evaluator
                     ├── Consistency Agent
                     └── Dialogue Agent
                              │
                    Image / TTS / Text Output
"""
from .base import BaseAgent
from .state import AgentState, NarrativeBeat, SessionPhase
from .orchestrator import AgentOrchestrator
from .director_agent import DirectorAgent
from .emotion_agent import EmotionAgent
from .world_simulator import WorldSimulator
from .event_agent import EventAgent
from .consistency_agent import ConsistencyAgent
from .dialogue_agent import DialogueAgent
from .memory import MemoryManager
from .narrative_beats import NARRATIVE_BEATS

__all__ = [
    "BaseAgent",
    "AgentState",
    "NarrativeBeat",
    "SessionPhase",
    "AgentOrchestrator",
    "DirectorAgent",
    "EmotionAgent",
    "WorldSimulator",
    "EventAgent",
    "ConsistencyAgent",
    "DialogueAgent",
    "MemoryManager",
    "NARRATIVE_BEATS",
]
