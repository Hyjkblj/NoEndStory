"""LLM 调用参数中心配置

按 call_type 统一管理 max_tokens / temperature / retry 策略。
支持环境变量覆盖，格式：LLM_CALL_{CALL_TYPE}_{PARAM}

例：
  LLM_CALL_DIALOGUE_MAX_TOKENS=120
  LLM_CALL_DIALOGUE_TEMPERATURE=0.8
  LLM_CALL_STORY_MAX_TOKENS=400
  LLM_MAX_RETRIES=2
  LLM_RETRY_DELAY=0.5
"""

import os
from dataclasses import dataclass
from typing import Dict


@dataclass
class CallParams:
    """单个调用类型的参数"""
    max_tokens: int
    temperature: float
    call_type: str  # 用于 TokenTracker 记录


# 默认参数表（按调用用途）
_DEFAULTS: Dict[str, CallParams] = {
    "story": CallParams(
        max_tokens=300,
        temperature=0.8,
        call_type="story",
    ),
    "dialogue": CallParams(
        max_tokens=100,
        temperature=0.9,
        call_type="dialogue",
    ),
    "options": CallParams(
        max_tokens=150,
        temperature=0.9,
        call_type="options",
    ),
    "supplement": CallParams(
        max_tokens=100,
        temperature=0.9,
        call_type="supplement",
    ),
    "event_context": CallParams(
        max_tokens=100,
        temperature=0.7,
        call_type="story",
    ),
    "scene_inference": CallParams(
        max_tokens=50,
        temperature=0.5,
        call_type="story",
    ),
    "continue_check": CallParams(
        max_tokens=20,
        temperature=0.3,
        call_type="dialogue",
    ),
}

# 全局重试配置
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("LLM_RETRY_DELAY", "1.0"))


def _load_env_overrides() -> Dict[str, CallParams]:
    """从环境变量加载覆盖值"""
    result = {}
    for name, params in _DEFAULTS.items():
        prefix = f"LLM_CALL_{name.upper()}_"
        max_tokens = int(os.getenv(f"{prefix}MAX_TOKENS", str(params.max_tokens)))
        temperature = float(os.getenv(f"{prefix}TEMPERATURE", str(params.temperature)))
        result[name] = CallParams(
            max_tokens=max_tokens,
            temperature=temperature,
            call_type=params.call_type,
        )
    return result


# 加载后的配置（含环境变量覆盖）
CALL_PARAMS: Dict[str, CallParams] = _load_env_overrides()


def get_call_params(call_type_or_name: str) -> CallParams:
    """获取指定调用类型的参数

    Args:
        call_type_or_name: 调用类型名称（如 "dialogue", "story", "options"）

    Returns:
        CallParams 实例。如果未找到，返回默认值 max_tokens=200, temperature=0.7。
    """
    if call_type_or_name in CALL_PARAMS:
        return CALL_PARAMS[call_type_or_name]
    # 兜底默认值
    return CallParams(max_tokens=200, temperature=0.7, call_type=call_type_or_name)
