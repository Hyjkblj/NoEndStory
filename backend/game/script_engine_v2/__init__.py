"""ScriptEngine V2 — 精简架构

4 组件：
  - ScriptEngine: 大脑+导演（生成所有交互数据）
  - WorldSimulator: 执行器（时间/天气/情绪应用）
  - ConsistencyAgent: 质量门（规则+可选LLM校验）
  - OrchestratorV2: 调度员（记忆/流水线/TTS）
"""
from .engine import ScriptEngine
from .models import RoundOutput, Option
from .world_simulator import WorldSimulator
from .consistency_agent import ConsistencyAgent
from .orchestrator import OrchestratorV2
from .llm_tool import LLMTool

__all__ = [
    "ScriptEngine",
    "RoundOutput",
    "Option",
    "WorldSimulator",
    "ConsistencyAgent",
    "OrchestratorV2",
    "LLMTool",
]
