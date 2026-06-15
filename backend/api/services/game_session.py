"""游戏会话管理（W8: PostgreSQL 持久化存储）"""
import uuid
import threading
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
from database.db_manager import DatabaseManager
from database.vector_db import VectorDatabase
from game.story_engine import StoryEngine
from game.event_generator import EventGenerator
from models.character import GameSession as GameSessionModel
from utils.logger import get_logger

logger = get_logger(__name__)

# 会话过期时间（小时）
SESSION_EXPIRE_HOURS = 24


class GameSession:
    """游戏会话（对应一个thread_id）"""
    def __init__(self, thread_id: str, user_id: str, character_id: int, game_mode: str):
        self.thread_id = thread_id
        self.user_id = user_id
        self.character_id = character_id
        self.game_mode = game_mode
        
        # 初始化游戏组件（添加日志）
        logger.info(f"正在初始化会话组件 (thread_id: {thread_id})...")
        logger.debug("初始化数据库管理器...")
        self.db_manager = DatabaseManager()
        logger.debug("初始化向量数据库...")
        self.vector_db = VectorDatabase()
        logger.debug("初始化事件生成器...")
        self.event_generator = EventGenerator(self.vector_db, self.db_manager)
        logger.debug("初始化故事引擎...")
        self.story_engine = StoryEngine(self.event_generator, self.db_manager)
        logger.info(f"会话初始化完成 (thread_id: {thread_id})")
        
        # 游戏状态
        self.is_initialized = False
        self.current_dialogue_round = None  # 当前对话轮次数据
        # 单会话串行锁，避免同一 thread 并发处理输入导致轮次错位
        self.lock = threading.RLock()
    
    def to_dict(self) -> dict:
        """序列化会话状态为字典"""
        return {
            'thread_id': self.thread_id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'game_mode': self.game_mode,
            'is_initialized': self.is_initialized,
            'current_scene': getattr(self.story_engine, 'current_scene', None),
            'current_dialogue_round': self.current_dialogue_round,
            # StoryEngine 状态需要单独序列化
            'story_engine_state': self._serialize_story_engine_state()
        }
    
    def _serialize_story_engine_state(self) -> dict:
        """序列化 StoryEngine 状态"""
        try:
            state = {
                'current_scene': getattr(self.story_engine, 'current_scene', None),
                'current_event': getattr(self.story_engine, 'current_event', None),
                'dialogue_history': getattr(self.story_engine, 'dialogue_history', []),
                'event_history': getattr(self.story_engine, 'event_history', []),
                'game_start_time': getattr(self.story_engine, 'game_start_time', None),
                'event_count': getattr(self.story_engine, 'event_count', 0),
            }
            return state
        except Exception as e:
            logger.warning(f"序列化 StoryEngine 状态失败: {e}")
            return {}
    
    @classmethod
    def from_dict(cls, data: dict, db_manager: DatabaseManager = None) -> 'GameSession':
        """从字典反序列化会话状态"""
        session = cls(
            thread_id=data['thread_id'],
            user_id=data['user_id'],
            character_id=data['character_id'],
            game_mode=data['game_mode']
        )
        
        # 恢复游戏状态
        session.is_initialized = data.get('is_initialized', False)
        session.current_dialogue_round = data.get('current_dialogue_round')
        
        # 恢复 StoryEngine 状态
        story_state = data.get('story_engine_state', {})
        if story_state and hasattr(session, 'story_engine'):
            session.story_engine.current_scene = story_state.get('current_scene')
            session.story_engine.current_event = story_state.get('current_event')
            session.story_engine.dialogue_history = story_state.get('dialogue_history', [])
            session.story_engine.event_history = story_state.get('event_history', [])
            session.story_engine.game_start_time = story_state.get('game_start_time')
            session.story_engine.event_count = story_state.get('event_count', 0)
        
        return session


class GameSessionManager:
    """游戏会话管理器（单例，线程安全，PostgreSQL 持久化）"""
    _instance = None
    _lock = threading.RLock()
    _sessions: Dict[str, GameSession] = {}  # 内存缓存
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameSessionManager, cls).__new__(cls)
            cls._instance._db_manager = DatabaseManager()
            cls._instance._load_sessions_from_db()
        return cls._instance
    
    def _load_sessions_from_db(self):
        """从数据库加载未过期的会话到内存缓存"""
        try:
            with self._db_manager.get_session() as session:
                # 查询未过期的会话
                now = datetime.utcnow()
                db_sessions = session.query(GameSessionModel).filter(
                    (GameSessionModel.expires_at > now) | (GameSessionModel.expires_at.is_(None))
                ).all()
                
                loaded_count = 0
                for db_session in db_sessions:
                    try:
                        # 反序列化会话状态
                        session_data = db_session.session_data or {}
                        game_session = GameSession.from_dict({
                            'thread_id': db_session.thread_id,
                            'user_id': db_session.user_id,
                            'character_id': db_session.character_id,
                            'game_mode': db_session.game_mode,
                            'is_initialized': bool(db_session.is_initialized),
                            'current_dialogue_round': session_data.get('current_dialogue_round'),
                            'story_engine_state': session_data.get('story_engine_state', {})
                        })
                        self._sessions[db_session.thread_id] = game_session
                        loaded_count += 1
                    except Exception as e:
                        logger.warning(f"加载会话 {db_session.thread_id} 失败: {e}")
                
                logger.info(f"从数据库加载了 {loaded_count} 个会话")
        except Exception as e:
            logger.error(f"从数据库加载会话失败: {e}", exc_info=True)
    
    def _save_session_to_db(self, session: GameSession):
        """将会话状态保存到数据库"""
        try:
            with self._db_manager.get_session() as db_session:
                # 查询是否已存在
                existing = db_session.query(GameSessionModel).filter(
                    GameSessionModel.thread_id == session.thread_id
                ).first()
                
                session_data = {
                    'current_dialogue_round': session.current_dialogue_round,
                    'story_engine_state': session._serialize_story_engine_state()
                }
                
                if existing:
                    # 更新现有会话
                    existing.is_initialized = 1 if session.is_initialized else 0
                    existing.current_scene = getattr(session.story_engine, 'current_scene', None)
                    existing.session_data = session_data
                    existing.updated_at = datetime.utcnow()
                else:
                    # 创建新会话
                    new_session = GameSessionModel(
                        thread_id=session.thread_id,
                        user_id=session.user_id,
                        character_id=session.character_id,
                        game_mode=session.game_mode,
                        is_initialized=1 if session.is_initialized else 0,
                        current_scene=getattr(session.story_engine, 'current_scene', None),
                        session_data=session_data,
                        expires_at=datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS)
                    )
                    db_session.add(new_session)
                
                db_session.commit()
                logger.debug(f"会话 {session.thread_id} 已保存到数据库")
        except Exception as e:
            logger.error(f"保存会话 {session.thread_id} 到数据库失败: {e}", exc_info=True)
    
    def create_session(
        self, 
        user_id: Optional[str], 
        character_id: int, 
        game_mode: str
    ) -> GameSession:
        """创建新游戏会话"""
        thread_id = str(uuid.uuid4())
        if not user_id:
            user_id = str(uuid.uuid4())
        
        session = GameSession(thread_id, user_id, character_id, game_mode)
        with self._lock:
            self._sessions[thread_id] = session
        
        # 保存到数据库
        self._save_session_to_db(session)
        
        return session
    
    def get_session(self, thread_id: str) -> Optional[GameSession]:
        """获取游戏会话（线程安全）"""
        with self._lock:
            session = self._sessions.get(thread_id)
            
            # 如果内存中没有，尝试从数据库加载
            if not session:
                try:
                    with self._db_manager.get_session() as db_session:
                        db_session_obj = db_session.query(GameSessionModel).filter(
                            GameSessionModel.thread_id == thread_id
                        ).first()
                        
                        if db_session_obj:
                            # 检查是否过期
                            if db_session_obj.expires_at and db_session_obj.expires_at < datetime.utcnow():
                                logger.warning(f"会话 {thread_id} 已过期")
                                return None
                            
                            # 反序列化
                            session_data = db_session_obj.session_data or {}
                            session = GameSession.from_dict({
                                'thread_id': db_session_obj.thread_id,
                                'user_id': db_session_obj.user_id,
                                'character_id': db_session_obj.character_id,
                                'game_mode': db_session_obj.game_mode,
                                'is_initialized': bool(db_session_obj.is_initialized),
                                'current_dialogue_round': session_data.get('current_dialogue_round'),
                                'story_engine_state': session_data.get('story_engine_state', {})
                            })
                            self._sessions[thread_id] = session
                            logger.info(f"从数据库加载会话 {thread_id}")
                except Exception as e:
                    logger.error(f"从数据库加载会话 {thread_id} 失败: {e}", exc_info=True)
            
            return session
    
    def delete_session(self, thread_id: str):
        """删除游戏会话（线程安全）"""
        with self._lock:
            if thread_id in self._sessions:
                del self._sessions[thread_id]
        
        # 从数据库删除
        try:
            with self._db_manager.get_session() as db_session:
                db_session.query(GameSessionModel).filter(
                    GameSessionModel.thread_id == thread_id
                ).delete()
                db_session.commit()
                logger.info(f"会话 {thread_id} 已从数据库删除")
        except Exception as e:
            logger.error(f"从数据库删除会话 {thread_id} 失败: {e}", exc_info=True)
    
    def get_all_sessions(self) -> Dict[str, GameSession]:
        """获取所有会话（线程安全）"""
        with self._lock:
            return self._sessions.copy()
    
    def save_session(self, thread_id: str):
        """手动保存指定会话到数据库"""
        with self._lock:
            session = self._sessions.get(thread_id)
            if session:
                self._save_session_to_db(session)
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        try:
            with self._db_manager.get_session() as db_session:
                now = datetime.utcnow()
                expired = db_session.query(GameSessionModel).filter(
                    GameSessionModel.expires_at < now
                ).all()
                
                expired_count = len(expired)
                for session in expired:
                    # 从内存缓存中删除
                    if session.thread_id in self._sessions:
                        del self._sessions[session.thread_id]
                
                # 从数据库删除
                db_session.query(GameSessionModel).filter(
                    GameSessionModel.expires_at < now
                ).delete()
                db_session.commit()
                
                if expired_count > 0:
                    logger.info(f"清理了 {expired_count} 个过期会话")
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}", exc_info=True)
