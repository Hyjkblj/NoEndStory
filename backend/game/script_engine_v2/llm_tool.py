"""LLMTool — LLM 推理工具封装

统一的 LLM 调用接口，封装 TextGenerationService。
"""
from typing import Optional
import asyncio
from utils.logger import get_logger

logger = get_logger("llm_tool")


class LLMTool:
    """LLM 推理工具"""

    def __init__(self, text_gen):
        """初始化

        Args:
            text_gen: TextGenerationService 实例
        """
        self.text_gen = text_gen

    async def generate(self, prompt: str, max_tokens: int = 200,
                       temperature: float = 0.7, call_type: str = "default") -> Optional[str]:
        """生成文本

        Args:
            prompt: 提示词
            max_tokens: 最大 token 数
            temperature: 温度
            call_type: 调用类型（用于 call_config 参数查找）

        Returns:
            生成的文本，失败返回 None
        """
        try:
            result = await asyncio.to_thread(
                self.generate_sync,
                prompt,
                max_tokens,
                temperature,
                call_type,
            )
            if result:
                return result
            logger.warning(
                "LLM 生成返回空结果: call_type=%s, prompt_len=%s",
                call_type,
                len(prompt),
            )
        except Exception as e:
            logger.warning(
                "LLM 生成失败: call_type=%s, prompt_len=%s, error=%s",
                call_type,
                len(prompt),
                e,
                exc_info=True,
            )
            return None

    def generate_sync(self, prompt: str, max_tokens: int = 200,
                      temperature: float = 0.7, call_type: str = "default") -> Optional[str]:
        """同步生成文本

        Args:
            prompt: 提示词
            max_tokens: 最大 token 数
            temperature: 温度
            call_type: 调用类型

        Returns:
            生成的文本，失败返回 None
        """
        try:
            from llm.call_config import get_call_params
            p = get_call_params(call_type)

            return self.text_gen._call_text_generation(
                prompt,
                max_tokens=p.max_tokens or max_tokens,
                temperature=p.temperature or temperature,
                call_type=call_type
            )
        except Exception as e:
            logger.warning(
                "LLM 同步生成失败: call_type=%s, prompt_len=%s, error=%s",
                call_type,
                len(prompt),
                e,
                exc_info=True,
            )
            return None
