"""安全管理员端点"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
from api.services.security_service import security_service
from api.middleware.cost_guard import CostTracker
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/admin/security", tags=["安全管理"])


@router.get("/banned-ips")
async def get_banned_ips():
    """
    获取所有被封禁的IP
    
    Returns:
        dict: 被封禁的IP列表
    """
    try:
        banned_ips = await security_service.get_banned_ips()
        return {
            "code": 200,
            "message": "success",
            "data": {
                "banned_ips": banned_ips,
                "total": len(banned_ips)
            }
        }
    except Exception as e:
        logger.error(f"获取封禁IP列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取封禁IP列表失败")


@router.post("/ban-ip")
async def ban_ip(
    ip: str = Query(..., description="要封禁的IP地址"),
    reason: str = Query(..., description="封禁原因"),
    duration_hours: Optional[int] = Query(None, description="封禁时长（小时），不填则为永久封禁")
):
    """
    手动封禁IP
    
    Args:
        ip: 要封禁的IP地址
        reason: 封禁原因
        duration_hours: 封禁时长（小时），None表示永久封禁
        
    Returns:
        dict: 操作结果
    """
    try:
        # 检查IP是否已被封禁
        is_banned, _ = await security_service.is_ip_banned(ip)
        if is_banned:
            return JSONResponse(
                status_code=400,
                content={
                    "code": 400,
                    "message": f"IP {ip} 已被封禁",
                    "data": None
                }
            )
        
        # 封禁IP
        permanent = duration_hours is None
        duration_seconds = duration_hours * 3600 if duration_hours else None
        
        await security_service.ban_ip(
            ip=ip,
            reason=reason,
            duration_seconds=duration_seconds,
            permanent=permanent
        )
        
        logger.info(f"管理员手动封禁IP: {ip}, 原因: {reason}, 时长: {duration_hours}小时")
        
        return {
            "code": 200,
            "message": f"IP {ip} 已封禁",
            "data": {
                "ip": ip,
                "reason": reason,
                "duration_hours": duration_hours,
                "permanent": permanent
            }
        }
    except Exception as e:
        logger.error(f"封禁IP失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="封禁IP失败")


@router.post("/unban-ip")
async def unban_ip(
    ip: str = Query(..., description="要解封的IP地址")
):
    """
    解封IP
    
    Args:
        ip: 要解封的IP地址
        
    Returns:
        dict: 操作结果
    """
    try:
        success = await security_service.unban_ip(ip)
        
        if success:
            logger.info(f"管理员解封IP: {ip}")
            return {
                "code": 200,
                "message": f"IP {ip} 已解封",
                "data": {"ip": ip}
            }
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "code": 404,
                    "message": f"IP {ip} 不在封禁列表中",
                    "data": None
                }
            )
    except Exception as e:
        logger.error(f"解封IP失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="解封IP失败")


@router.get("/ip-behavior/{ip}")
async def get_ip_behavior(ip: str):
    """
    获取IP行为记录
    
    Args:
        ip: 客户端IP
        
    Returns:
        dict: IP行为记录
    """
    try:
        behavior = await security_service.get_ip_behavior(ip)
        
        if behavior:
            return {
                "code": 200,
                "message": "success",
                "data": behavior
            }
        else:
            return {
                "code": 200,
                "message": "未找到该IP的行为记录",
                "data": None
            }
    except Exception as e:
        logger.error(f"获取IP行为记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取IP行为记录失败")


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000),
    action: Optional[str] = Query(None, description="过滤操作类型")
):
    """
    获取审计日志
    
    Args:
        limit: 返回数量限制
        action: 过滤操作类型
        
    Returns:
        dict: 审计日志列表
    """
    try:
        logs = await security_service.get_audit_logs(limit=limit, action=action)
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "logs": logs,
                "total": len(logs)
            }
        }
    except Exception as e:
        logger.error(f"获取审计日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取审计日志失败")


@router.get("/stats")
async def get_security_stats():
    """
    获取安全统计信息
    
    Returns:
        dict: 安全统计信息
    """
    try:
        stats = await security_service.get_stats()
        
        return {
            "code": 200,
            "message": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取安全统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取安全统计失败")


@router.get("/cost-stats")
async def get_cost_stats():
    """
    获取成本统计信息
    
    Returns:
        dict: 成本统计信息
    """
    try:
        # 这里需要访问CostTracker实例，暂时返回模拟数据
        # 实际实现需要注入CostTracker实例
        return {
            "code": 200,
            "message": "success",
            "data": {
                "note": "成本统计需要从CostGuard中间件获取",
                "suggestion": "请通过中间件响应头查看实时成本信息"
            }
        }
    except Exception as e:
        logger.error(f"获取成本统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取成本统计失败")