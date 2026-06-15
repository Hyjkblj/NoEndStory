"""管理统计 API

提供可观测性数据的管理端点：
- 健康检查增强
- Token 用量统计
- 系统使用概览
- 近期 LLM 调用记录
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime

from monitoring.token_tracker import get_token_tracker
from monitoring.usage_stats import get_usage_stats
from monitoring.health import get_health_checker
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/admin/stats", tags=["管理统计"])


# ==================== 健康检查 ====================

@router.get("/health")
async def enhanced_health_check():
    """
    增强健康检查
    
    检查数据库、向量数据库、LLM 提供商、静态文件目录。
    
    Returns:
        dict: 各组件健康状态
    """
    try:
        checker = get_health_checker()
        result = checker.full_check()
        status_code = 200 if result["status"] != "unhealthy" else 503
        return JSONResponse(status_code=status_code, content={
            "code": status_code,
            "message": f"系统状态: {result['status']}",
            "data": result
        })
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="健康检查执行失败")


# ==================== Token 用量统计 ====================

@router.get("/tokens/daily")
async def get_token_daily_stats(
    days: int = Query(30, description="查询天数", ge=1, le=365)
):
    """
    获取每日 Token 用量统计
    
    Args:
        days: 查询最近 N 天
        
    Returns:
        dict: 每日 Token 统计
    """
    try:
        tracker = get_token_tracker()
        stats = tracker.get_daily_stats(days=days)
        return {
            "code": 200,
            "message": "success",
            "data": {
                "days": days,
                "daily": stats
            }
        }
    except Exception as e:
        logger.error(f"获取每日 Token 统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取 Token 统计失败")


@router.get("/tokens/hourly")
async def get_token_hourly_stats(
    hours: int = Query(24, description="查询小时数", ge=1, le=168)
):
    """
    获取每小时 Token 用量统计
    
    Args:
        hours: 查询最近 N 小时
        
    Returns:
        dict: 每小时 Token 统计
    """
    try:
        tracker = get_token_tracker()
        stats = tracker.get_hourly_stats(hours=hours)
        return {
            "code": 200,
            "message": "success",
            "data": {
                "hours": hours,
                "hourly": stats
            }
        }
    except Exception as e:
        logger.error(f"获取每小时 Token 统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取 Token 统计失败")


@router.get("/tokens/today")
async def get_token_today_stats():
    """
    获取今日 Token 用量统计
    
    Returns:
        dict: 今日 Token 统计（含按类型明细）
    """
    try:
        tracker = get_token_tracker()
        stats = tracker.get_today_stats()
        return {
            "code": 200,
            "message": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取今日 Token 统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取 Token 统计失败")


@router.get("/tokens/total")
async def get_token_total_stats():
    """
    获取总计 Token 用量统计
    
    Returns:
        dict: 总计统计（含错误率）
    """
    try:
        tracker = get_token_tracker()
        stats = tracker.get_total_stats()
        return {
            "code": 200,
            "message": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取总计 Token 统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取 Token 统计失败")


@router.get("/tokens/recent")
async def get_token_recent_records(
    limit: int = Query(50, description="返回记录数", ge=1, le=500)
):
    """
    获取最近的 LLM 调用记录
    
    Args:
        limit: 返回记录数
        
    Returns:
        dict: 最近 N 条调用记录
    """
    try:
        tracker = get_token_tracker()
        records = tracker.get_recent_records(limit=limit)
        return {
            "code": 200,
            "message": "success",
            "data": {
                "count": len(records),
                "records": records
            }
        }
    except Exception as e:
        logger.error(f"获取最近 Token 记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取 Token 记录失败")


# ==================== 系统使用概览 ====================

@router.get("/dashboard")
async def get_admin_dashboard():
    """
    管理面板概览
    
    汇总会话、角色、事件、Token 消耗等关键指标。
    
    Returns:
        dict: 管理面板概览数据
    """
    try:
        stats_service = get_usage_stats()
        tracker = get_token_tracker()
        
        dashboard = stats_service.get_dashboard_summary()
        dashboard["tokens"] = tracker.get_today_stats()
        dashboard["tokens_total"] = tracker.get_total_stats()
        
        return {
            "code": 200,
            "message": "success",
            "data": dashboard
        }
    except Exception as e:
        logger.error(f"获取管理面板概览失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取概览数据失败")


@router.get("/sessions")
async def get_game_sessions_stats(
    days: int = Query(7, description="查询天数", ge=1, le=90)
):
    """
    游戏会话统计
    
    Args:
        days: 查询最近 N 天
        
    Returns:
        dict: 会话统计数据
    """
    try:
        stats_service = get_usage_stats()
        data = stats_service.get_game_sessions_stats(days=days)
        return {
            "code": 200,
            "message": "success",
            "data": data
        }
    except Exception as e:
        logger.error(f"获取会话统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取会话统计失败")


@router.get("/characters")
async def get_character_stats():
    """
    角色创建统计
    
    Returns:
        dict: 角色统计数据
    """
    try:
        stats_service = get_usage_stats()
        data = stats_service.get_character_stats()
        return {
            "code": 200,
            "message": "success",
            "data": data
        }
    except Exception as e:
        logger.error(f"获取角色统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取角色统计失败")


@router.get("/events")
async def get_events_stats(
    days: int = Query(7, description="查询天数", ge=1, le=90)
):
    """
    故事事件统计
    
    Args:
        days: 查询最近 N 天
        
    Returns:
        dict: 事件统计数据（含同步状态）
    """
    try:
        stats_service = get_usage_stats()
        data = stats_service.get_story_events_stats(days=days)
        return {
            "code": 200,
            "message": "success",
            "data": data
        }
    except Exception as e:
        logger.error(f"获取事件统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取事件统计失败")


@router.get("/completion-rate")
async def get_game_completion_rate():
    """
    游戏完成率
    
    Returns:
        dict: 完成率数据
    """
    try:
        stats_service = get_usage_stats()
        data = stats_service.get_game_completion_rate()
        return {
            "code": 200,
            "message": "success",
            "data": data
        }
    except Exception as e:
        logger.error(f"获取完成率失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取完成率失败")
