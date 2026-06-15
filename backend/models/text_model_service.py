"""文本大模型服务（W9a: 已合并到 TextGenerationService）

此模块保留作为向后兼容层，委托给 TextGenerationService。
新代码请直接使用：
    from game.ai_generator import TextGenerationService
"""
from typing import Optional, List, Dict, Any
from game.ai_generator import TextGenerationService as _TextGenerationService


class TextModelService(_TextGenerationService):
    """文本大模型服务（兼容包装器，委托给 TextGenerationService）
    
    W9a 重构后，核心功能已合并到 game/ai_generator.py 中的 TextGenerationService。
    此类保留用于向后兼容。
    """
    
    def __init__(self, provider: Optional[str] = None, **kwargs):
        """初始化（委托给 TextGenerationService）"""
        # 忽略旧版 config 参数
        kwargs.pop('config', None)
        super().__init__(provider=provider, **kwargs)
    
    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        use_retry: bool = True,
        **kwargs
    ) -> Optional[str]:
        """生成文本（委托给统一接口）"""
        return self._call_text_generation(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_message=system_message
        )
