"""请求日志中间件

记录所有 API 调用的：
- 请求方法、路径、查询参数
- 客户端 IP
- 响应状态码
- 处理耗时
- User-Agent

可通过环境变量 REQUEST_LOG_ENABLED=false 关闭。
"""

import time
import os
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from utils.logger import setup_logger

logger = setup_logger(__name__)

# 不记录日志的路径（健康检查、静态文件等）
EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json", "/favicon.ico", "/redoc"}
EXCLUDED_PREFIXES = ("/static/", "/admin/static/")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件
    
    记录每个 HTTP 请求的详细信息。
    在开发环境默认启用，生产环境可通过环境变量控制。
    """
    
    def __init__(self, app: ASGIApp, log_body: bool = False, max_body_length: int = 500):
        super().__init__(app)
        self.log_body = log_body
        self.max_body_length = max_body_length
        self._enabled = os.getenv("REQUEST_LOG_ENABLED", "true").lower() in ("true", "1", "yes")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._enabled:
            return await call_next(request)
        
        # 跳过排除的路径
        path = request.url.path
        if path in EXCLUDED_PATHS or path.startswith(EXCLUDED_PREFIXES):
            return await call_next(request)
        
        start_time = time.time()
        status_code = 500  # 默认值
        
        # 获取客户端信息
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        method = request.method
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            # 构建日志消息
            log_data = {
                "method": method,
                "path": path,
                "query": str(request.query_params) if request.query_params else "",
                "status": status_code,
                "duration_ms": round(duration_ms, 1),
                "client_ip": client_ip,
            }
            
            # 根据状态码选择日志级别
            if status_code >= 500:
                logger.error(f"请求异常: {method} {path} → {status_code} ({duration_ms:.1f}ms) [{client_ip}]")
            elif status_code >= 400:
                logger.warning(f"请求错误: {method} {path} → {status_code} ({duration_ms:.1f}ms) [{client_ip}]")
            elif duration_ms > 3000:
                logger.warning(f"慢请求: {method} {path} → {status_code} ({duration_ms:.1f}ms) [{client_ip}]")
            else:
                logger.info(f"请求: {method} {path} → {status_code} ({duration_ms:.1f}ms) [{client_ip}]")


def create_request_logging_middleware(app: ASGIApp) -> RequestLoggingMiddleware:
    """创建请求日志中间件的工厂函数"""
    return RequestLoggingMiddleware(app)
