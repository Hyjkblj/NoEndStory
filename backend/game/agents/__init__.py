"""NOS Agent 引擎（6 Agent + 状态机 + Redis/PG 双层记忆）

架构:
    Director Agent ──┬── Emotion Agent
                     ├── World Simulator
                     ├── Event Agent
                     ├── Consistency Agent
                     └── Dialogue Agent
                              │
                    Image / TTS / Text Output

记忆架构:
    Redis (短期) ──事件结束──▶ PostgreSQL (长期)
"""
from .base import BaseAgent
from .state import AgentState, NarrativeBeat, SessionPhase, EmotionState, WorldState
from .orchestrator import AgentOrchestrator
from .director_agent import DirectorAgent
from .emotion_agent import EmotionAgent
from .world_simulator import WorldSimulator
from .event_agent import EventAgent
from .consistency_agent import ConsistencyAgent
from .dialogue_agent import DialogueAgent
from .memory import MemoryManager
from .redis_memory import RedisMemoryStore
from .pg_memory import PgMemoryStore
from .narrative_beats import NARRATIVE_BEATS

__all__ = [
    "BaseAgent",
    "AgentState",
    "NarrativeBeat",
    "SessionPhase",
    "EmotionState",
    "WorldState",
    "AgentOrchestrator",
    "DirectorAgent",
    "EmotionAgent",
    "WorldSimulator",
    "EventAgent",
    "ConsistencyAgent",
    "DialogueAgent",
    "MemoryManager",
    "RedisMemoryStore",
    "PgMemoryStore",
    "NARRATIVE_BEATS",
]
