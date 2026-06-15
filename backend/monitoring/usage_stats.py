"""使用统计聚合查询

提供按用户/IP/端点/时间维度的聚合统计查询。
从数据库读取审计日志、GameSession 和 StoryEvent 数据。
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import threading

from database.db_manager import DatabaseManager
from sqlalchemy import text, func
from utils.logger import setup_logger

logger = setup_logger(__name__)


class UsageStats:
    """使用统计聚合器（线程安全的单例）"""
    
    _instance: Optional["UsageStats"] = None
    _lock = threading.Lock()
    
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
        self._db = DatabaseManager()
        logger.info("UsageStats 已初始化")
    
    def get_game_sessions_stats(self, days: int = 7) -> Dict:
        """获取游戏会话统计
        
        Returns:
            {
                "total_sessions": N,
                "active_sessions": N,
                "avg_duration_minutes": N,
                "daily": [...]
            }
        """
        try:
            with self._db.get_session() as session:
                # 总会话数
                total = session.execute(
                    text("SELECT COUNT(*) FROM game_sessions")
                ).scalar() or 0
                
                # 活跃会话数（未过期）
                active = session.execute(
                    text("SELECT COUNT(*) FROM game_sessions WHERE expires_at > NOW()")
                ).scalar() or 0
                
                # 平均游戏时长
                avg_duration = session.execute(
                    text("""
                        SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60)
                        FROM game_sessions
                        WHERE is_initialized = true
                    """)
                ).scalar()
                avg_duration = round(float(avg_duration or 0), 1)
                
                # 每日新增
                daily = session.execute(
                    text("""
                        SELECT DATE(created_at) as date, COUNT(*) as count
                        FROM game_sessions
                        WHERE created_at > NOW() - :days * INTERVAL '1 day'
                        GROUP BY DATE(created_at)
                        ORDER BY date
                    """),
                    {"days": days}
                ).fetchall()
                
                return {
                    "total_sessions": total,
                    "active_sessions": active,
                    "avg_duration_minutes": avg_duration,
                    "daily": [
                        {"date": str(row[0]), "count": row[1]}
                        for row in daily
                    ]
                }
        except Exception as e:
            logger.error(f"获取游戏会话统计失败: {e}")
            return {"error": str(e), "total_sessions": 0, "active_sessions": 0, "avg_duration_minutes": 0, "daily": []}
    
    def get_character_stats(self) -> Dict:
        """获取角色创建统计"""
        try:
            with self._db.get_session() as session:
                # 总角色数
                total = session.execute(
                    text("SELECT COUNT(*) FROM characters WHERE deleted_at IS NULL")
                ).scalar() or 0
                
                # 已删除角色数
                deleted = session.execute(
                    text("SELECT COUNT(*) FROM characters WHERE deleted_at IS NOT NULL")
                ).scalar() or 0
                
                # 热门场景 Top 10
                top_scenes = session.execute(
                    text("""
                        SELECT scene_id, COUNT(*) as count
                        FROM characters
                        WHERE deleted_at IS NULL AND scene_id IS NOT NULL
                        GROUP BY scene_id
                        ORDER BY count DESC
                        LIMIT 10
                    """)
                ).fetchall()
                
                return {
                    "total_characters": total,
                    "deleted_characters": deleted,
                    "deletion_rate": round(deleted / max(total + deleted, 1) * 100, 2),
                    "top_scenes": [
                        {"scene_id": str(row[0]), "count": row[1]}
                        for row in top_scenes
                    ]
                }
        except Exception as e:
            logger.error(f"获取角色统计失败: {e}")
            return {"error": str(e), "total_characters": 0}
    
    def get_story_events_stats(self, days: int = 7) -> Dict:
        """获取故事事件统计"""
        try:
            with self._db.get_session() as session:
                # 总事件数
                total = session.execute(
                    text("SELECT COUNT(*) FROM story_events")
                ).scalar() or 0
                
                # 同步状态分布
                sync_status = session.execute(
                    text("""
                        SELECT sync_status, COUNT(*) as count
                        FROM story_events
                        GROUP BY sync_status
                    """)
                ).fetchall()
                
                # 每日新增
                daily = session.execute(
                    text("""
                        SELECT DATE(created_at) as date, COUNT(*) as count
                        FROM story_events
                        WHERE created_at > NOW() - :days * INTERVAL '1 day'
                        GROUP BY DATE(created_at)
                        ORDER BY date
                    """),
                    {"days": days}
                ).fetchall()
                
                return {
                    "total_events": total,
                    "sync_status": [
                        {"status": str(row[0]), "count": row[1]}
                        for row in sync_status
                    ],
                    "daily": [
                        {"date": str(row[0]), "count": row[1]}
                        for row in daily
                    ]
                }
        except Exception as e:
            logger.error(f"获取故事事件统计失败: {e}")
            return {"error": str(e), "total_events": 0}
    
    def get_game_completion_rate(self, days: int = 7) -> Dict:
        """获取游戏完成率（含有多轮对话的会话比例）"""
        try:
            with self._db.get_session() as session:
                # 有初始化且至少有事件的会话
                total_initialized = session.execute(
                    text("SELECT COUNT(*) FROM game_sessions WHERE is_initialized = true")
                ).scalar() or 0
                
                # 有事件的会话
                sessions_with_events = session.execute(
                    text("""
                        SELECT COUNT(DISTINCT gs.id)
                        FROM game_sessions gs
                        INNER JOIN story_events se ON se.character_id = gs.character_id
                        WHERE gs.is_initialized = true
                    """)
                ).scalar() or 0
                
                return {
                    "total_initialized_sessions": total_initialized,
                    "sessions_with_events": sessions_with_events,
                    "completion_rate": round(
                        sessions_with_events / max(total_initialized, 1) * 100, 2
                    )
                }
        except Exception as e:
            logger.error(f"获取游戏完成率失败: {e}")
            return {"error": str(e), "total_initialized_sessions": 0}
    
    def get_dashboard_summary(self) -> Dict:
        """获取管理面板概览数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "sessions": self.get_game_sessions_stats(days=7),
            "characters": self.get_character_stats(),
            "events": self.get_story_events_stats(days=7),
            "completion": self.get_game_completion_rate(),
        }
    
    def reset(self):
        """重置（无状态，仅占位）"""
        pass


# 全局单例
_usage_stats: Optional[UsageStats] = None


def get_usage_stats() -> UsageStats:
    """获取 UsageStats 单例"""
    global _usage_stats
    if _usage_stats is None:
        _usage_stats = UsageStats()
    return _usage_stats
