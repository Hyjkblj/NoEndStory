"""成本监控中间件"""
import time
import asyncio
from typing import Dict, Optional, Tuple
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class CostTracker:
    """成本追踪器"""
    
    def __init__(self, hourly_limit: float = 2.0, daily_limit: float = 5.0):
        """
        初始化成本追踪器
        
        Args:
            hourly_limit: 每小时成本限制（美元）
            daily_limit: 每日成本限制（美元）
        """
        self.hourly_limit = hourly_limit
        self.daily_limit = daily_limit
        
        # 按IP存储成本记录 {ip: [(timestamp, cost_usd), ...]}
        self.cost_records: Dict[str, list] = {}
        self._lock = asyncio.Lock()
        
        # 统计信息
        self.total_cost = 0.0
        self.total_requests = 0
        
        logger.info(f"成本追踪器初始化: 每小时限制=${hourly_limit}, 每日限制=${daily_limit}")
    
    async def record_cost(self, ip: str, cost_usd: float, endpoint: str = None):
        """
        记录成本
        
        Args:
            ip: 客户端IP
            cost_usd: 成本（美元）
            endpoint: 端点路径
        """
        async with self._lock:
            current_time = time.time()
            
            if ip not in self.cost_records:
                self.cost_records[ip] = []
            
            # 记录成本
            self.cost_records[ip].append({
                'timestamp': current_time,
                'cost_usd': cost_usd,
                'endpoint': endpoint
            })
            
            # 更新统计
            self.total_cost += cost_usd
            self.total_requests += 1
            
            # 清理旧记录（保留24小时）
            cutoff_time = current_time - 86400  # 24小时前
            self.cost_records[ip] = [
                record for record in self.cost_records[ip]
                if record['timestamp'] > cutoff_time
            ]
            
            logger.debug(f"成本记录: IP={ip}, 成本=${cost_usd:.4f}, 端点={endpoint}")
    
    async def get_ip_costs(self, ip: str) -> Tuple[float, float]:
        """
        获取IP的成本统计
        
        Args:
            ip: 客户端IP
            
        Returns:
            Tuple[float, float]: (过去1小时成本, 过去24小时成本)
        """
        async with self._lock:
            if ip not in self.cost_records:
                return 0.0, 0.0
            
            current_time = time.time()
            hourly_cutoff = current_time - 3600  # 1小时前
            daily_cutoff = current_time - 86400  # 24小时前
            
            hourly_cost = 0.0
            daily_cost = 0.0
            
            for record in self.cost_records[ip]:
                if record['timestamp'] > hourly_cutoff:
                    hourly_cost += record['cost_usd']
                if record['timestamp'] > daily_cutoff:
                    daily_cost += record['cost_usd']
            
            return hourly_cost, daily_cost
    
    async def is_over_limit(self, ip: str) -> Tuple[bool, str, float, float]:
        """
        检查是否超过成本限制
        
        Args:
            ip: 客户端IP
            
        Returns:
            Tuple[bool, str, float, float]: (是否超过限制, 原因, 当前成本, 限制)
        """
        hourly_cost, daily_cost = await self.get_ip_costs(ip)
        
        # 检查小时限制
        if hourly_cost >= self.hourly_limit:
            return True, "hourly_limit_exceeded", hourly_cost, self.hourly_limit
        
        # 检查日限制
        if daily_cost >= self.daily_limit:
            return True, "daily_limit_exceeded", daily_cost, self.daily_limit
        
        return False, "", 0.0, 0.0
    
    async def get_stats(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        async with self._lock:
            return {
                'total_cost': self.total_cost,
                'total_requests': self.total_requests,
                'active_ips': len(self.cost_records),
                'hourly_limit': self.hourly_limit,
                'daily_limit': self.daily_limit
            }


class CostGuardMiddleware(BaseHTTPMiddleware):
    """
    成本监控中间件
    
    功能：
    1. 记录每次API调用的成本
    2. 监控Token消耗
    3. 自动熔断（超过限制返回429）
    4. 成本统计
    """
    
    def __init__(
        self,
        app,
        hourly_limit: float = 2.0,
        daily_limit: float = 5.0,
        cost_per_request: float = 0.01,
        excluded_paths: list = None
    ):
        """
        初始化成本监控中间件
        
        Args:
            app: FastAPI应用
            hourly_limit: 每小时成本限制（美元）
            daily_limit: 每日成本限制（美元）
            cost_per_request: 每个请求的基础成本（美元）
            excluded_paths: 排除的路径列表
        """
        super().__init__(app)
        self.hourly_limit = hourly_limit
        self.daily_limit = daily_limit
        self.cost_per_request = cost_per_request
        
        # 排除的路径（健康检查、文档等）
        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
            "/favicon.ico"
        ]
        
        # 端点特定成本配置 {path_pattern: cost_usd}
        self.endpoint_costs = {
            "/api/v1/game/init": 0.05,  # 游戏初始化成本较高
            "/api/v1/game/input": 0.02,  # 游戏输入成本
            "/api/v1/characters/create": 0.03,  # 角色创建成本
            "/api/v1/tts": 0.01,  # TTS成本
            "/api/v1/images/generate": 0.10,  # 图片生成成本
        }
        
        # 成本追踪器
        self.cost_tracker = CostTracker(
            hourly_limit=hourly_limit,
            daily_limit=daily_limit
        )
        
        # 从环境变量读取配置
        self._load_config_from_env()
        
        logger.info(f"成本监控中间件初始化完成: 每小时限制=${hourly_limit}, 每日限制=${daily_limit}")
    
    def _load_config_from_env(self):
        """从环境变量加载配置"""
        # 每小时成本限制
        hourly_limit = os.getenv('COST_LIMIT_PER_IP_HOURLY')
        if hourly_limit:
            try:
                self.hourly_limit = float(hourly_limit)
                self.cost_tracker.hourly_limit = self.hourly_limit
                logger.info(f"从环境变量加载每小时成本限制: ${self.hourly_limit}")
            except ValueError:
                logger.warning(f"环境变量 COST_LIMIT_PER_IP_HOURLY 格式错误: {hourly_limit}")
        
        # 每日成本限制
        daily_limit = os.getenv('COST_LIMIT_PER_IP_DAILY')
        if daily_limit:
            try:
                self.daily_limit = float(daily_limit)
                self.cost_tracker.daily_limit = self.daily_limit
                logger.info(f"从环境变量加载每日成本限制: ${self.daily_limit}")
            except ValueError:
                logger.warning(f"环境变量 COST_LIMIT_PER_IP_DAILY 格式错误: {daily_limit}")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端真实IP地址
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            str: 客户端IP地址
        """
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 取第一个IP（客户端真实IP）
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # 直接连接
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_excluded_path(self, path: str) -> bool:
        """
        检查路径是否被排除
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否被排除
        """
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    def _get_endpoint_cost(self, path: str) -> float:
        """
        获取端点特定的成本
        
        Args:
            path: 请求路径
            
        Returns:
            float: 成本（美元）
        """
        for pattern, cost in self.endpoint_costs.items():
            if path.startswith(pattern):
                return cost
        
        # 默认成本
        return self.cost_per_request
    
    async def _check_cost_limit(self, ip: str) -> Tuple[bool, str, float, float]:
        """
        检查成本限制
        
        Args:
            ip: 客户端IP
            
        Returns:
            Tuple[bool, str, float, float]: (是否超过限制, 原因, 当前成本, 限制)
        """
        return await self.cost_tracker.is_over_limit(ip)
    
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
        
        # 检查成本限制
        is_over_limit, reason, current_cost, limit = await self._check_cost_limit(client_ip)
        
        if is_over_limit:
            logger.warning(f"成本限制触发: IP={client_ip}, 原因={reason}, 当前成本=${current_cost:.2f}, 限制=${limit:.2f}")
            
            if reason == "hourly_limit_exceeded":
                message = "每小时API调用成本已达上限，请稍后再试"
                retry_after = 3600  # 1小时
            else:  # daily_limit_exceeded
                message = "每日API调用成本已达上限，请明天再试"
                retry_after = 86400  # 24小时
            
            return JSONResponse(
                status_code=429,
                content={
                    "code": 429,
                    "message": message,
                    "data": {
                        "reason": reason,
                        "current_cost": round(current_cost, 2),
                        "limit": round(limit, 2),
                        "retry_after": retry_after
                    }
                },
                headers={
                    "X-CostLimit-Limit": str(limit),
                    "X-CostLimit-Current": str(round(current_cost, 2)),
                    "Retry-After": str(retry_after)
                }
            )
        
        # 记录请求成本
        cost = self._get_endpoint_cost(path)
        await self.cost_tracker.record_cost(client_ip, cost, path)
        
        # 继续处理请求
        response = await call_next(request)
        
        # 添加成本响应头
        hourly_cost, daily_cost = await self.cost_tracker.get_ip_costs(client_ip)
        response.headers["X-CostLimit-Hourly-Limit"] = str(self.hourly_limit)
        response.headers["X-CostLimit-Hourly-Remaining"] = str(round(self.hourly_limit - hourly_cost, 2))
        response.headers["X-CostLimit-Daily-Limit"] = str(self.daily_limit)
        response.headers["X-CostLimit-Daily-Remaining"] = str(round(self.daily_limit - daily_cost, 2))
        
        return response


# 创建中间件实例
def create_cost_guard_middleware(
    hourly_limit: float = 2.0,
    daily_limit: float = 5.0,
    cost_per_request: float = 0.01,
    excluded_paths: list = None
):
    """
    创建成本监控中间件工厂函数
    
    Args:
        hourly_limit: 每小时成本限制（美元）
        daily_limit: 每日成本限制（美元）
        cost_per_request: 每个请求的基础成本（美元）
        excluded_paths: 排除的路径列表
        
    Returns:
        CostGuardMiddleware: 中间件类
    """
    class ConfiguredCostGuardMiddleware(CostGuardMiddleware):
        def __init__(self, app):
            super().__init__(
                app,
                hourly_limit=hourly_limit,
                daily_limit=daily_limit,
                cost_per_request=cost_per_request,
                excluded_paths=excluded_paths
            )
    
    return ConfiguredCostGuardMiddleware