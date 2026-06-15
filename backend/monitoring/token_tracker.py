"""Token 消耗追踪器

记录每次 LLM 调用的 input/output tokens 和成本。
通过 monkey-patch LLMService.call_with_retry 自动拦截所有 LLM 调用。
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class TokenRecord:
    """单次 LLM 调用的 token 记录"""
    timestamp: float
    provider: str
    model: str
    call_type: str          # 调用类型：story/dialogue/options/supplement
    input_tokens: int
    output_tokens: int
    cost_usd: float         # 美元成本
    duration_ms: float      # 调用耗时（毫秒）
    success: bool
    error: str = ""


# 各模型的 token 定价（每 1K tokens，USD）
# 参考 2024-2025 主流模型定价
MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    # DeepSeek
    "deepseek-chat": {"input": 0.00027, "output": 0.0011},
    "deepseek-reasoner": {"input": 0.00055, "output": 0.00219},
    # 火山引擎（豆包）
    "doubao-pro-32k": {"input": 0.0008, "output": 0.002},
    "doubao-lite-32k": {"input": 0.0003, "output": 0.0006},
    # 阿里 DashScope（通义千问）
    "qwen-turbo": {"input": 0.0004, "output": 0.0008},
    "qwen-plus": {"input": 0.002, "output": 0.006},
    "qwen-max": {"input": 0.02, "output": 0.06},
    # 默认兜底
    "default": {"input": 0.001, "output": 0.002},
}


def _estimate_tokens(text: str) -> int:
    """粗略估算文本的 token 数量（中英文混合）
    
    中文：约 1.5 字符/token
    英文：约 4 字符/token（OpenAI 标准）
    """
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4)


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """计算单次调用的成本（USD）"""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 6)


class TokenTracker:
    """Token 消耗追踪器（线程安全的单例）"""
    
    _instance: Optional["TokenTracker"] = None
    _lock = threading.Lock()
    
    # 内存存储：最近 N 条记录 + 聚合数据
    MAX_RECORDS = 10000
    BUCKET_HOURLY = timedelta(hours=1)
    BUCKET_DAILY = timedelta(days=1)
    RETENTION_HOURS = 72  # 保留 72 小时数据
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._records: List[TokenRecord] = []
        self._lock = threading.Lock()
        
        # 按小时的聚合数据：{hour_key: {"input": N, "output": N, "cost": N, "calls": N}}
        self._hourly_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"input_tokens": 0, "output_tokens": 0, "cost": 0.0, "calls": 0, "errors": 0}
        )
        # 按天的聚合数据
        self._daily_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"input_tokens": 0, "output_tokens": 0, "cost": 0.0, "calls": 0, "errors": 0}
        )
        # 按天+调用类型的聚合
        self._daily_by_type: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(
                lambda: {"input_tokens": 0, "output_tokens": 0, "cost": 0.0, "calls": 0}
            )
        )
        
        self._started_at = datetime.now()
        logger.info("TokenTracker 已初始化")
    
    def record(
        self,
        provider: str,
        model: str,
        call_type: str,
        prompt: str,
        response_text: str,
        usage: Optional[Dict] = None,
        duration_ms: float = 0,
        success: bool = True,
        error: str = ""
    ):
        """记录一次 LLM 调用
        
        Args:
            provider: LLM 提供商
            model: 模型名称
            call_type: 调用类型（story/dialogue/options/supplement）
            prompt: 输入提示词
            response_text: 输出文本
            usage: API 返回的 usage 数据（可选，含精确 token 数）
            duration_ms: 调用耗时
            success: 是否成功
            error: 错误信息
        """
        # 计算 tokens
        if usage:
            input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
        else:
            input_tokens = _estimate_tokens(prompt)
            output_tokens = _estimate_tokens(response_text or "")
        
        cost = calculate_cost(model, input_tokens, output_tokens) if success else 0.0
        
        record = TokenRecord(
            timestamp=time.time(),
            provider=provider,
            model=model,
            call_type=call_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )
        
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%dT%H")
        day_key = now.strftime("%Y-%m-%d")
        
        with self._lock:
            self._records.append(record)
            # 限制记录数量
            if len(self._records) > self.MAX_RECORDS:
                self._records = self._records[-self.MAX_RECORDS:]
            
            # 更新聚合数据
            self._hourly_stats[hour_key]["input_tokens"] += input_tokens
            self._hourly_stats[hour_key]["output_tokens"] += output_tokens
            self._hourly_stats[hour_key]["cost"] += cost
            self._hourly_stats[hour_key]["calls"] += 1
            if not success:
                self._hourly_stats[hour_key]["errors"] += 1
            
            self._daily_stats[day_key]["input_tokens"] += input_tokens
            self._daily_stats[day_key]["output_tokens"] += output_tokens
            self._daily_stats[day_key]["cost"] += cost
            self._daily_stats[day_key]["calls"] += 1
            if not success:
                self._daily_stats[day_key]["errors"] += 1
            
            self._daily_by_type[day_key][call_type]["input_tokens"] += input_tokens
            self._daily_by_type[day_key][call_type]["output_tokens"] += output_tokens
            self._daily_by_type[day_key][call_type]["cost"] += cost
            self._daily_by_type[day_key][call_type]["calls"] += 1
        
        logger.debug(
            f"Token 记录: provider={provider}, model={model}, type={call_type}, "
            f"input={input_tokens}, output={output_tokens}, cost=${cost:.6f}, "
            f"duration={duration_ms:.0f}ms"
        )
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict]:
        """获取最近 N 小时的统计"""
        with self._lock:
            now = datetime.now()
            result = []
            for i in range(hours):
                t = now - timedelta(hours=i)
                key = t.strftime("%Y-%m-%dT%H")
                stats = dict(self._hourly_stats.get(key, {}))
                stats["hour"] = key
                stats["cost"] = round(stats.get("cost", 0), 6)
                result.append(stats)
            # 按时间正序
            result.reverse()
            return result
    
    def get_daily_stats(self, days: int = 30) -> List[Dict]:
        """获取最近 N 天的统计"""
        with self._lock:
            now = datetime.now()
            result = []
            for i in range(days):
                t = now - timedelta(days=i)
                key = t.strftime("%Y-%m-%d")
                stats = dict(self._daily_stats.get(key, {}))
                stats["date"] = key
                stats["cost"] = round(stats.get("cost", 0), 6)
                # 添加按类型的明细
                if key in self._daily_by_type:
                    stats["by_type"] = {
                        ct: dict(d) for ct, d in self._daily_by_type[key].items()
                    }
                result.append(stats)
            result.reverse()
            return result
    
    def get_today_stats(self) -> Dict:
        """获取今日统计"""
        today = datetime.now().strftime("%Y-%m-%d")
        with self._lock:
            stats = dict(self._daily_stats.get(today, {}))
            stats["date"] = today
            stats["cost"] = round(stats.get("cost", 0), 6)
            if today in self._daily_by_type:
                stats["by_type"] = {
                    ct: dict(d) for ct, d in self._daily_by_type[today].items()
                }
            return stats
    
    def get_total_stats(self) -> Dict:
        """获取总计统计"""
        with self._lock:
            total_input = sum(d["input_tokens"] for d in self._daily_stats.values())
            total_output = sum(d["output_tokens"] for d in self._daily_stats.values())
            total_cost = sum(d["cost"] for d in self._daily_stats.values())
            total_calls = sum(d["calls"] for d in self._daily_stats.values())
            total_errors = sum(d["errors"] for d in self._daily_stats.values())
            return {
                "total_input_tokens": int(total_input),
                "total_output_tokens": int(total_output),
                "total_cost_usd": round(total_cost, 6),
                "total_calls": int(total_calls),
                "total_errors": int(total_errors),
                "error_rate": round(total_errors / max(total_calls, 1) * 100, 2),
                "started_at": self._started_at.isoformat(),
            }
    
    def get_recent_records(self, limit: int = 50) -> List[Dict]:
        """获取最近 N 条调用记录"""
        with self._lock:
            records = self._records[-limit:]
            return [
                {
                    "timestamp": datetime.fromtimestamp(r.timestamp).isoformat(),
                    "provider": r.provider,
                    "model": r.model,
                    "call_type": r.call_type,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost_usd": r.cost_usd,
                    "duration_ms": r.duration_ms,
                    "success": r.success,
                    "error": r.error,
                }
                for r in records
            ]
    
    def reset(self):
        """重置所有数据（用于测试）"""
        with self._lock:
            self._records.clear()
            self._hourly_stats.clear()
            self._daily_stats.clear()
            self._daily_by_type.clear()
            self._started_at = datetime.now()
            logger.info("TokenTracker 数据已重置")


# 全局单例
_token_tracker: Optional[TokenTracker] = None


def get_token_tracker() -> TokenTracker:
    """获取 TokenTracker 单例"""
    global _token_tracker
    if _token_tracker is None:
        _token_tracker = TokenTracker()
    return _token_tracker


def install_token_tracking():
    """安装 Token 追踪：monkey-patch LLMService 以自动记录"""
    try:
        from llm.base import LLMService
        
        original_call_with_retry = LLMService.call_with_retry
        original_chat_completion = LLMService.chat_completion
        
        async def tracked_call_with_retry(self, messages, max_tokens=None, 
                                          temperature=None, max_retries=3,
                                          retry_delay=1.0, **kwargs):
            """带 token 追踪的 call_with_retry"""
            from llm.providers.base import LLMResponse
            tracker = get_token_tracker()
            start = time.time()
            success = True
            error_msg = ""
            result = None
            
            try:
                result = original_call_with_retry(
                    self, messages=messages, max_tokens=max_tokens,
                    temperature=temperature, max_retries=max_retries,
                    retry_delay=retry_delay, **kwargs
                )
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration_ms = (time.time() - start) * 1000
                # 从 messages 提取 prompt 文本
                prompt_text = ""
                for msg in messages:
                    prompt_text += msg.get("content", "") + "\n"
                
                usage = result.usage if (success and isinstance(result, LLMResponse)) else None
                response_text = result.text if (success and isinstance(result, LLMResponse)) else ""
                
                tracker.record(
                    provider=self.provider_name,
                    model=self.get_model(),
                    call_type="unknown",  # 由 chat_completion 层覆盖
                    prompt=prompt_text,
                    response_text=response_text,
                    usage=usage,
                    duration_ms=duration_ms,
                    success=success,
                    error=error_msg,
                )
            
            return result
        
        def tracked_chat_completion(self, prompt, max_tokens=200, temperature=0.7,
                                     system_message=None, use_retry=True, 
                                     call_type="unknown", **kwargs):
            """带 token 追踪的 chat_completion"""
            tracker = get_token_tracker()
            start = time.time()
            success = True
            error_msg = ""
            result_text = ""
            
            try:
                result_text = original_chat_completion(
                    self, prompt=prompt, max_tokens=max_tokens,
                    temperature=temperature, system_message=system_message,
                    use_retry=use_retry, **kwargs
                )
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration_ms = (time.time() - start) * 1000
                tracker.record(
                    provider=self.provider_name,
                    model=self.get_model(),
                    call_type=call_type,
                    prompt=prompt,
                    response_text=result_text,
                    usage=None,
                    duration_ms=duration_ms,
                    success=success,
                    error=error_msg,
                )
            
            return result_text
        
        # 应用 monkey-patch
        LLMService.call_with_retry = tracked_call_with_retry
        LLMService.chat_completion = tracked_chat_completion
        
        logger.info("Token 追踪已安装到 LLMService")
    except ImportError as e:
        logger.warning(f"无法安装 Token 追踪（LLM 模块未加载）: {e}")
    except Exception as e:
        logger.error(f"安装 Token 追踪时发生错误: {e}", exc_info=True)
