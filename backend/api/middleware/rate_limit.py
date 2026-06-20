"""请求频率限制中间件"""
import time
import asyncio
from typing import Dict, Optional, Tuple
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from api.utils.network import get_client_ip
from utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class SlidingWindowCounter:
    """滑动窗口计数器"""
    
    def __init__(self, window_size: int = 3600):
        """
        初始化滑动窗口计数器
        
        Args:
            window_size: 窗口大小（秒），默认1小时
        """
        self.window_size = window_size
        self.requests: Dict[str, list] = {}  # {key: [timestamp1, timestamp2, ...]}
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, max_requests: int) -> Tuple[bool, int, int]:
        """
        检查请求是否被允许
        
        Args:
            key: 限流键（通常是IP地址或IP+端点）
            max_requests: 窗口内最大请求数
            
        Returns:
            Tuple[bool, int, int]: (是否允许, 当前计数, 剩余配额)
        """
        async with self._lock:
            current_time = time.time()
            
            # 初始化或获取请求列表
            if key not in self.requests:
                self.requests[key] = []
            
            # 清理过期请求
            self.requests[key] = [
                ts for ts in self.requests[key] 
                if current_time - ts < self.window_size
            ]
            
            current_count = len(self.requests[key])
            
            if current_count >= max_requests:
                # 计算需要等待的时间
                oldest_request = self.requests[key][0]
                wait_time = int(self.window_size - (current_time - oldest_request))
                return False, current_count, 0
            
            # 记录当前请求
            self.requests[key].append(current_time)
            return True, current_count + 1, max_requests - current_count - 1


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    请求频率限制中间件
    
    功能：
    1. IP级别请求频率限制
    2. 端点差异化配置
    3. 游客免费次数限制（24h/3次）
    4. 滑动窗口算法
    """
    
    def __init__(
        self,
        app,
        default_max_requests: int = 100,
        default_window_seconds: int = 3600,
        guest_max_plays_per_day: int = 100,
        excluded_paths: list = None
    ):
        """
        初始化频率限制中间件
        
        Args:
            app: FastAPI应用
            default_max_requests: 默认最大请求数（每窗口）
            default_window_seconds: 默认窗口大小（秒）
            guest_max_plays_per_day: 游客每天最大游戏次数
            excluded_paths: 排除的路径列表（不进行限流）
        """
        super().__init__(app)
        self.default_max_requests = default_max_requests
        self.default_window_seconds = default_window_seconds
        self.guest_max_plays_per_day = guest_max_plays_per_day
        
        # 排除的路径（健康检查、文档等）
        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
            "/favicon.ico"
        ]
        
        # 端点特定配置 {path_pattern: (max_requests, window_seconds)}
        self.endpoint_limits = {
            "/api/v1/game/init": (10, 3600),  # 游戏初始化：每小时10次
            "/api/v1/game/input": (100, 3600),  # 游戏输入：每小时100次
            "/api/v1/characters/create": (5, 3600),  # 角色创建：每小时5次
        }
        
        # IP级别的滑动窗口计数器
        self.ip_counter = SlidingWindowCounter(window_size=self.default_window_seconds)
        
        # 游客游戏次数计数器（24小时窗口）
        self.guest_play_counter = SlidingWindowCounter(window_size=86400)  # 24小时
        
        # 端点特定计数器
        self.endpoint_counters: Dict[str, SlidingWindowCounter] = {}
        
        # 从环境变量读取配置
        self._load_config_from_env()
        
        logger.info(f"频率限制中间件初始化完成: 默认限制={default_max_requests}/{default_window_seconds}s, 游客限制={guest_max_plays_per_day}次/天")
    
    def _load_config_from_env(self):
        """从环境变量加载配置"""
        # 游客免费次数
        guest_free_plays = os.getenv('GUEST_FREE_PLAYS')
        if guest_free_plays:
            try:
                self.guest_max_plays_per_day = int(guest_free_plays)
                logger.info(f"从环境变量加载游客免费次数限制: {self.guest_max_plays_per_day}")
            except ValueError:
                logger.warning(f"环境变量 GUEST_FREE_PLAYS 格式错误: {guest_free_plays}")
        
        # IP级别每日免费次数
        ip_daily_limit = os.getenv('GUEST_MAX_FREE_PLAYS_PER_IP_PER_DAY')
        if ip_daily_limit:
            try:
                # 更新游客游戏次数限制
                self.guest_max_plays_per_day = int(ip_daily_limit)
                logger.info(f"从环境变量加载IP每日免费次数限制: {self.guest_max_plays_per_day}")
            except ValueError:
                logger.warning(f"环境变量 GUEST_MAX_FREE_PLAYS_PER_IP_PER_DAY 格式错误: {ip_daily_limit}")
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP 地址（委托给公共函数）"""
        return get_client_ip(request)
    
    def _is_excluded_path(self, path: str) -> bool:
        """
        检查路径是否被排除
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否被排除
        """
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    def _get_endpoint_key(self, path: str) -> Optional[str]:
        """
        获取端点特定的限流键
        
        Args:
            path: 请求路径
            
        Returns:
            Optional[str]: 端点特定键，如果没有特定配置则返回None
        """
        for pattern in self.endpoint_limits.keys():
            if path.startswith(pattern):
                return pattern
        return None
    
    def _is_guest_play_endpoint(self, path: str) -> bool:
        """
        检查是否是游客游戏端点
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否是游客游戏端点
        """
        # 游客游戏端点（需要消耗免费次数）
        guest_play_paths = [
            "/api/v1/game/init",
            "/api/v1/game/input"
        ]
        return any(path.startswith(p) for p in guest_play_paths)
    
    def _is_guest_user(self, request: Request) -> bool:
        """
        检查是否是游客用户
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            bool: 是否是游客用户
        """
        # 检查Authorization头
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return True  # 没有认证头，视为游客
        
        # 检查是否是游客token（简单检查，实际应该验证token类型）
        # 这里简化处理，实际应该解析JWT token
        return False
    
    async def _check_ip_limit(self, client_ip: str) -> Tuple[bool, int, int]:
        """
        检查IP级别限制
        
        Args:
            client_ip: 客户端IP
            
        Returns:
            Tuple[bool, int, int]: (是否允许, 当前计数, 剩余配额)
        """
        return await self.ip_counter.is_allowed(
            f"ip:{client_ip}", 
            self.default_max_requests
        )
    
    async def _check_endpoint_limit(self, client_ip: str, endpoint_key: str) -> Tuple[bool, int, int]:
        """
        检查端点特定限制
        
        Args:
            client_ip: 客户端IP
            endpoint_key: 端点键
            
        Returns:
            Tuple[bool, int, int]: (是否允许, 当前计数, 剩余配额)
        """
        if endpoint_key not in self.endpoint_counters:
            max_requests, window_seconds = self.endpoint_limits[endpoint_key]
            self.endpoint_counters[endpoint_key] = SlidingWindowCounter(window_size=window_seconds)
        
        counter = self.endpoint_counters[endpoint_key]
        max_requests, _ = self.endpoint_limits[endpoint_key]
        
        return await counter.is_allowed(
            f"endpoint:{endpoint_key}:{client_ip}",
            max_requests
        )
    
    async def _check_guest_play_limit(self, client_ip: str) -> Tuple[bool, int, int]:
        """
        检查游客游戏次数限制
        
        Args:
            client_ip: 客户端IP
            
        Returns:
            Tuple[bool, int, int]: (是否允许, 当前计数, 剩余配额)
        """
        return await self.guest_play_counter.is_allowed(
            f"guest_play:{client_ip}",
            self.guest_max_plays_per_day
        )
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求
        
        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: 响应对象
        """
        # 获取请求路径
        path = request.url.path
        
        # 检查是否排除
        if self._is_excluded_path(path):
            return await call_next(request)
        
        # 获取客户端IP
        client_ip = self._get_client_ip(request)
        
        # 检查IP级别限制
        ip_allowed, ip_count, ip_remaining = await self._check_ip_limit(client_ip)
        if not ip_allowed:
            logger.warning(f"IP频率限制触发: IP={client_ip}, 请求数={ip_count}")
            return JSONResponse(
                status_code=429,
                content={
                    "code": 429,
                    "message": "请求过于频繁，请稍后再试",
                    "data": {
                        "retry_after": self.default_window_seconds,
                        "limit": self.default_max_requests,
                        "remaining": 0
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(self.default_max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + self.default_window_seconds),
                    "Retry-After": str(self.default_window_seconds)
                }
            )
        
        # 检查端点特定限制
        endpoint_key = self._get_endpoint_key(path)
        if endpoint_key:
            endpoint_allowed, endpoint_count, endpoint_remaining = await self._check_endpoint_limit(
                client_ip, endpoint_key
            )
            if not endpoint_allowed:
                max_requests, window_seconds = self.endpoint_limits[endpoint_key]
                logger.warning(f"端点频率限制触发: IP={client_ip}, 端点={endpoint_key}, 请求数={endpoint_count}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": 429,
                        "message": f"该接口请求过于频繁，请稍后再试",
                        "data": {
                            "retry_after": window_seconds,
                            "limit": max_requests,
                            "remaining": 0
                        }
                    },
                    headers={
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + window_seconds),
                        "Retry-After": str(window_seconds)
                    }
                )
        
        # 检查游客游戏次数限制
        if self._is_guest_play_endpoint(path) and self._is_guest_user(request):
            guest_allowed, guest_count, guest_remaining = await self._check_guest_play_limit(client_ip)
            if not guest_allowed:
                logger.warning(f"游客游戏次数限制触发: IP={client_ip}, 次数={guest_count}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": 429,
                        "message": "游客免费游戏次数已用完，请注册账号继续游戏",
                        "data": {
                            "limit": self.guest_max_plays_per_day,
                            "remaining": 0,
                            "register_required": True
                        }
                    },
                    headers={
                        "X-GuestPlayLimit": str(self.guest_max_plays_per_day),
                        "X-GuestPlayRemaining": "0"
                    }
                )
        
        # 继续处理请求
        response = await call_next(request)
        
        # 添加限流响应头
        response.headers["X-RateLimit-Limit"] = str(self.default_max_requests)
        response.headers["X-RateLimit-Remaining"] = str(ip_remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.default_window_seconds)
        
        return response


# 创建中间件实例
def create_rate_limit_middleware(
    default_max_requests: int = 100,
    default_window_seconds: int = 3600,
    guest_max_plays_per_day: int = 100,
    excluded_paths: list = None
):
    """
    创建频率限制中间件工厂函数
    
    Args:
        default_max_requests: 默认最大请求数
        default_window_seconds: 默认窗口大小（秒）
        guest_max_plays_per_day: 游客每天最大游戏次数
        excluded_paths: 排除的路径列表
        
    Returns:
        RateLimitMiddleware: 中间件类
    """
    class ConfiguredRateLimitMiddleware(RateLimitMiddleware):
        def __init__(self, app):
            super().__init__(
                app,
                default_max_requests=default_max_requests,
                default_window_seconds=default_window_seconds,
                guest_max_plays_per_day=guest_max_plays_per_day,
                excluded_paths=excluded_paths
            )
    
    return ConfiguredRateLimitMiddleware