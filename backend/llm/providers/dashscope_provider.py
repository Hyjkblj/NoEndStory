"""通义千问（DashScope）提供商适配器（兼容OpenAI SDK格式）"""

from typing import List, Dict, Optional, Any

try:
    import dashscope
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    dashscope = None
    Generation = None

from .base import ProviderAdapter, LLMResponse
from ..exceptions import LLMProviderError, LLMAccountError, LLMNetworkError


class DashScopeProvider(ProviderAdapter):
    """通义千问（DashScope）提供商适配器（兼容OpenAI格式）"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化DashScope适配器
        
        Args:
            config: 配置字典，包含：
                - api_key: API密钥
                - model: 模型名称
        """
        if not DASHSCOPE_AVAILABLE:
            raise ImportError("dashscope未安装，请运行: pip install dashscope")
        
        super().__init__(config)
        
        # 设置API密钥
        dashscope.api_key = self.api_key
    
    def call(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """调用DashScope API（转换为DashScope格式）
        
        Args:
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            LLMResponse对象
        """
        try:
            # DashScope使用不同的格式，需要转换messages
            # DashScope的Generation.call需要prompt参数
            # 我们将messages转换为prompt字符串
            prompt_parts = []
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'system':
                    prompt_parts.append(f"系统: {content}")
                elif role == 'user':
                    prompt_parts.append(f"用户: {content}")
                elif role == 'assistant':
                    prompt_parts.append(f"助手: {content}")
            
            prompt = "\n".join(prompt_parts)
            
            # 构建请求参数
            params = {
                "model": self.model,
                "prompt": prompt,
            }
            
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            if temperature is not None:
                params["temperature"] = temperature
            
            # 添加其他参数（DashScope支持的）
            if 'top_p' in kwargs:
                params["top_p"] = kwargs['top_p']
            if 'top_k' in kwargs:
                params["top_k"] = kwargs['top_k']
            
            # 调用API
            response = Generation.call(**params)
            
            # 检查响应状态
            if response.status_code == 200:
                output_text = response.output.text.strip() if response.output.text else ""
                
                return LLMResponse(
                    text=output_text,
                    model=self.model,
                    usage={
                        "prompt_tokens": getattr(response.usage, 'input_tokens', 0) if hasattr(response, 'usage') else 0,
                        "completion_tokens": getattr(response.usage, 'output_tokens', 0) if hasattr(response, 'usage') else 0,
                        "total_tokens": getattr(response.usage, 'input_tokens', 0) + getattr(response.usage, 'output_tokens', 0) if hasattr(response, 'usage') else 0,
                    } if hasattr(response, 'usage') else None,
                    finish_reason=None,  # DashScope不提供finish_reason
                    raw_response=response
                )
            else:
                error_message = response.message or ''
                
                # 检测账户相关错误
                is_account_error = any(keyword in error_message.lower() for keyword in [
                    'access denied', 'account', 'overdue', 'payment', 'good standing',
                    '账户', '欠费', '余额', '权限', 'invalid', 'unauthorized'
                ])
                
                if is_account_error:
                    raise LLMAccountError(f"通义千问账户问题: {error_message}")
                else:
                    raise LLMProviderError(f"通义千问API调用失败: {error_message}")
                    
        except LLMAccountError:
            raise
        except LLMProviderError:
            raise
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() or "network" in error_msg.lower():
                raise LLMNetworkError(f"通义千问API网络错误: {error_msg}")
            else:
                raise LLMProviderError(f"通义千问API调用异常: {error_msg}")
