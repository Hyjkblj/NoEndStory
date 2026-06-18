"""PostgreSQL 长期记忆存储

存储事件摘要、角色知识、玩家偏好、对话摘要。
事件结束后从 Redis 压缩写入。

表结构:
  - game_events: 游戏事件（事件级压缩存储）
  - character_knowledge: 角色知识（从事件中提取）
  - player_preferences: 玩家偏好（跨会话持久化）
"""
import json
from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class PgMemoryStore:
    """PostgreSQL 长期记忆存储"""

    def __init__(self, db_manager):
        self.db = db_manager

    # ========== 事件存储 ==========

    def save_event(self, character_id: int, thread_id: str, event_data: dict) -> Optional[int]:
        """保存事件（事件结束时调用）

        Args:
            character_id: 角色 ID
            thread_id: 会话 ID
            event_data: 事件数据字典

        Returns:
            事件 ID，失败返回 None
        """
        try:
            with self.db.get_session() as session:
                result = session.execute("""
                    INSERT INTO game_events
                    (character_id, thread_id, event_type, event_summary, scene,
                     emotion_start, emotion_end, emotion_delta,
                     round_count, player_choices, world_state,
                     game_round_start, game_round_end)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    character_id, thread_id,
                    event_data.get('event_type', 'unknown'),
                    event_data.get('event_summary', ''),
                    event_data.get('scene'),
                    json.dumps(event_data.get('emotion_start', {})),
                    json.dumps(event_data.get('emotion_end', {})),
                    json.dumps(event_data.get('emotion_delta', {})),
                    event_data.get('round_count', 0),
                    json.dumps(event_data.get('player_choices', [])),
                    json.dumps(event_data.get('world_state', {})),
                    event_data.get('game_round_start'),
                    event_data.get('game_round_end'),
                ))
                event_id = result.fetchone()[0] if result else None
                logger.info(f"事件保存成功: id={event_id}, type={event_data.get('event_type')}")
                return event_id
        except Exception as e:
            logger.error(f"事件保存失败: {e}")
            return None

    def get_recent_events(self, character_id: int, n: int = 5) -> List[Dict]:
        """获取最近 N 个事件"""
        try:
            with self.db.get_session() as session:
                results = session.execute("""
                    SELECT id, event_type, event_summary, scene,
                           emotion_end, round_count, created_at
                    FROM game_events
                    WHERE character_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (character_id, n)).fetchall()
                return [dict(r) for r in results]
        except Exception as e:
            logger.error(f"获取事件失败: {e}")
            return []

    def get_event_count(self, character_id: int, thread_id: str) -> int:
        """获取会话内的事件数量"""
        try:
            with self.db.get_session() as session:
                result = session.execute("""
                    SELECT COUNT(*) FROM game_events
                    WHERE character_id = %s AND thread_id = %s
                """, (character_id, thread_id)).fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"获取事件数量失败: {e}")
            return 0

    def get_thread_events(self, character_id: int, thread_id: str) -> List[Dict]:
        """获取会话内的所有事件"""
        try:
            with self.db.get_session() as session:
                results = session.execute("""
                    SELECT id, event_type, event_summary, scene,
                           emotion_start, emotion_end, emotion_delta,
                           round_count, player_choices, game_round_start, game_round_end
                    FROM game_events
                    WHERE character_id = %s AND thread_id = %s
                    ORDER BY created_at ASC
                """, (character_id, thread_id)).fetchall()
                return [dict(r) for r in results]
        except Exception as e:
            logger.error(f"获取会话事件失败: {e}")
            return []

    # ========== 知识存储 ==========

    def save_knowledge(self, character_id: int, knowledge_type: str,
                       content: str, importance: float = 0.5,
                       source_event_id: int = None, source_thread_id: str = None) -> bool:
        """保存角色知识"""
        try:
            with self.db.get_session() as session:
                session.execute("""
                    INSERT INTO character_knowledge
                    (character_id, knowledge_type, content, importance,
                     source_event_id, source_thread_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (character_id, knowledge_type, content, importance,
                      source_event_id, source_thread_id))
                logger.debug(f"知识保存成功: type={knowledge_type}")
                return True
        except Exception as e:
            logger.error(f"知识保存失败: {e}")
            return False

    def get_knowledge(self, character_id: int, knowledge_type: str = None,
                      limit: int = 10) -> List[Dict]:
        """获取角色知识"""
        try:
            with self.db.get_session() as session:
                if knowledge_type:
                    results = session.execute("""
                        SELECT id, knowledge_type, content, importance,
                               source_event_id, created_at
                        FROM character_knowledge
                        WHERE character_id = %s AND knowledge_type = %s
                        ORDER BY importance DESC, created_at DESC
                        LIMIT %s
                    """, (character_id, knowledge_type, limit)).fetchall()
                else:
                    results = session.execute("""
                        SELECT id, knowledge_type, content, importance,
                               source_event_id, created_at
                        FROM character_knowledge
                        WHERE character_id = %s
                        ORDER BY importance DESC, created_at DESC
                        LIMIT %s
                    """, (character_id, limit)).fetchall()
                return [dict(r) for r in results]
        except Exception as e:
            logger.error(f"获取知识失败: {e}")
            return []

    def update_knowledge_access(self, knowledge_id: int):
        """更新知识访问时间和次数"""
        try:
            with self.db.get_session() as session:
                session.execute("""
                    UPDATE character_knowledge
                    SET access_count = access_count + 1, last_accessed = NOW()
                    WHERE id = %s
                """, (knowledge_id,))
        except Exception as e:
            logger.warning(f"更新知识访问失败: {e}")

    # ========== 偏好存储 ==========

    def update_preference(self, character_id: int, preference_type: str,
                          preference_value: dict) -> bool:
        """更新玩家偏好（upsert）"""
        try:
            with self.db.get_session() as session:
                session.execute("""
                    INSERT INTO player_preferences
                    (character_id, preference_type, preference_value, sample_count, confidence)
                    VALUES (%s, %s, %s, 1, 0.5)
                    ON CONFLICT (character_id, preference_type) DO UPDATE
                    SET preference_value = %s,
                        sample_count = player_preferences.sample_count + 1,
                        confidence = LEAST(1.0, player_preferences.confidence + 0.05),
                        updated_at = NOW()
                """, (character_id, preference_type, json.dumps(preference_value),
                      json.dumps(preference_value)))
                return True
        except Exception as e:
            logger.error(f"更新偏好失败: {e}")
            return False

    def get_preferences(self, character_id: int) -> List[Dict]:
        """获取玩家偏好"""
        try:
            with self.db.get_session() as session:
                results = session.execute("""
                    SELECT preference_type, preference_value, sample_count, confidence
                    FROM player_preferences
                    WHERE character_id = %s
                    ORDER BY confidence DESC
                """, (character_id,)).fetchall()
                return [dict(r) for r in results]
        except Exception as e:
            logger.error(f"获取偏好失败: {e}")
            return []
