"""Redis 短期记忆存储

存储单个事件内的对话历史、情绪快照、世界状态。
事件结束后清理，压缩摘要存入 PostgreSQL。

Key 结构:
  noendstory:session:{thread_id} → Hash {
    working_memory, emotion_snapshot, world_state,
    narrative_state, current_event, metadata
  }
  TTL: 24 小时
"""
import json
import time
from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class RedisMemoryStore:
    """Redis 短期记忆存储"""

    KEY_PREFIX = "noendstory:session:"
    TTL = 86400  # 24 小时

    def __init__(self, redis_client):
        self.redis = redis_client

    def _key(self, thread_id: str) -> str:
        return f"{self.KEY_PREFIX}{thread_id}"

    # ========== 初始化 ==========

    def init_session(self, thread_id: str, character_id: int, character_name: str,
                     emotion_snapshot: dict = None, world_state: dict = None):
        """初始化会话记忆"""
        key = self._key(thread_id)
        now = int(time.time())

        default_emotion = {
            "favorability": 50.0, "trust": 50.0, "hostility": 0.0,
            "dependence": 50.0, "emotion": 50.0, "stress": 0.0,
            "anxiety": 0.0, "happiness": 50.0, "sadness": 0.0,
            "confidence": 50.0, "initiative": 50.0, "caution": 0.0,
        }
        default_world = {
            "current_scene": "classroom", "current_time": "morning",
            "weather": "clear", "elapsed_minutes": 0.0,
            "time_of_day_progress": 0.0,
        }

        pipe = self.redis.pipeline()
        pipe.hset(key, "working_memory", "[]")
        pipe.hset(key, "emotion_snapshot", json.dumps(emotion_snapshot or default_emotion))
        pipe.hset(key, "world_state", json.dumps(world_state or default_world))
        pipe.hset(key, "narrative_state", json.dumps({
            "phase": "opening", "total_rounds": 0, "round_count": 0,
            "current_event_type": None, "current_beat_name": "开场相识",
            "used_events": [],
        }))
        pipe.hset(key, "current_event", "{}")
        pipe.hset(key, "metadata", json.dumps({
            "character_id": character_id,
            "character_name": character_name,
            "created_at": now,
            "last_updated": now,
        }))
        pipe.expire(key, self.TTL)
        pipe.execute()
        logger.debug(f"Redis 会话初始化: {thread_id}")

    # ========== 读取 ==========

    def load_working_memory(self, thread_id: str) -> List[Dict]:
        data = self.redis.hget(self._key(thread_id), "working_memory")
        return json.loads(data) if data else []

    def load_emotion_snapshot(self, thread_id: str) -> Dict:
        data = self.redis.hget(self._key(thread_id), "emotion_snapshot")
        return json.loads(data) if data else {}

    def load_world_state(self, thread_id: str) -> Dict:
        data = self.redis.hget(self._key(thread_id), "world_state")
        return json.loads(data) if data else {}

    def load_narrative_state(self, thread_id: str) -> Dict:
        data = self.redis.hget(self._key(thread_id), "narrative_state")
        return json.loads(data) if data else {}

    def load_current_event(self, thread_id: str) -> Dict:
        data = self.redis.hget(self._key(thread_id), "current_event")
        return json.loads(data) if data else {}

    def load_metadata(self, thread_id: str) -> Dict:
        data = self.redis.hget(self._key(thread_id), "metadata")
        return json.loads(data) if data else {}

    def load_all(self, thread_id: str) -> Dict[str, Any]:
        """一次性加载所有记忆（减少 Redis 往返）"""
        key = self._key(thread_id)
        data = self.redis.hgetall(key)
        if not data:
            return {}

        # hgetall 返回 bytes，需要解码
        decoded = {}
        for k, v in data.items():
            key_str = k.decode() if isinstance(k, bytes) else k
            val_str = v.decode() if isinstance(v, bytes) else v
            decoded[key_str] = val_str

        return {
            "working_memory": json.loads(decoded.get("working_memory", "[]")),
            "emotion_snapshot": json.loads(decoded.get("emotion_snapshot", "{}")),
            "world_state": json.loads(decoded.get("world_state", "{}")),
            "narrative_state": json.loads(decoded.get("narrative_state", "{}")),
            "current_event": json.loads(decoded.get("current_event", "{}")),
            "metadata": json.loads(decoded.get("metadata", "{}")),
        }

    def exists(self, thread_id: str) -> bool:
        """检查会话是否存在"""
        return self.redis.exists(self._key(thread_id)) > 0

    # ========== 写入（原子操作） ==========

    def save_round(self, thread_id: str, player_input: str, character_dialogue: str,
                   emotion_snapshot: dict, world_state: dict, narrative_state: dict):
        """保存一轮对话（原子操作，保证一致性）"""
        key = self._key(thread_id)

        # 读取现有对话历史
        working_memory = self.load_working_memory(thread_id)
        round_num = len(working_memory) // 2 + 1
        timestamp = int(time.time())

        # 追加本轮对话
        working_memory.append({
            "role": "player", "content": player_input,
            "round": round_num, "timestamp": timestamp,
        })
        working_memory.append({
            "role": "character", "content": character_dialogue,
            "round": round_num, "timestamp": timestamp,
        })

        # 限制最大条数（保留最近 40 条 = 20 轮）
        if len(working_memory) > 40:
            working_memory = working_memory[-40:]

        # 更新 metadata
        metadata = self.load_metadata(thread_id)
        metadata["last_updated"] = timestamp

        # 原子写入
        pipe = self.redis.pipeline()
        pipe.hset(key, "working_memory", json.dumps(working_memory))
        pipe.hset(key, "emotion_snapshot", json.dumps(emotion_snapshot))
        pipe.hset(key, "world_state", json.dumps(world_state))
        pipe.hset(key, "narrative_state", json.dumps(narrative_state))
        pipe.hset(key, "metadata", json.dumps(metadata))
        pipe.expire(key, self.TTL)
        pipe.execute()

    def save_current_event(self, thread_id: str, event: dict):
        """保存当前事件信息"""
        self.redis.hset(self._key(thread_id), "current_event", json.dumps(event))

    def save_emotion_snapshot(self, thread_id: str, emotion_snapshot: dict):
        """单独更新情绪快照"""
        self.redis.hset(self._key(thread_id), "emotion_snapshot", json.dumps(emotion_snapshot))

    def save_world_state(self, thread_id: str, world_state: dict):
        """单独更新世界状态"""
        self.redis.hset(self._key(thread_id), "world_state", json.dumps(world_state))

    def save_narrative_state(self, thread_id: str, narrative_state: dict):
        """单独更新叙事状态"""
        self.redis.hset(self._key(thread_id), "narrative_state", json.dumps(narrative_state))

    # ========== 事件结束 ==========

    def load_event_data(self, thread_id: str) -> Dict[str, Any]:
        """加载事件完整数据（事件结束时调用）"""
        return self.load_all(thread_id)

    def clear_event_data(self, thread_id: str):
        """清理事件数据（保留 emotion/world/narrative/metadata）"""
        key = self._key(thread_id)
        pipe = self.redis.pipeline()
        pipe.hset(key, "working_memory", "[]")
        pipe.hset(key, "current_event", "{}")
        pipe.execute()

    # ========== 清理 ==========

    def delete_session(self, thread_id: str):
        """删除会话记忆"""
        self.redis.delete(self._key(thread_id))

    def extend_ttl(self, thread_id: str):
        """续期 TTL"""
        self.redis.expire(self._key(thread_id), self.TTL)
