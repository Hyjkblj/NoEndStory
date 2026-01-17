"""游戏会话管理"""
import uuid
from typing import Dict, Optional
from database.db_manager import DatabaseManager
from database.vector_db import VectorDatabase
from game.story_engine import StoryEngine
from game.event_generator import EventGenerator


class GameSession:
    """游戏会话（对应一个thread_id）"""
    def __init__(self, thread_id: str, user_id: str, character_id: int, game_mode: str):
        self.thread_id = thread_id
        self.user_id = user_id
        self.character_id = character_id
        self.game_mode = game_mode
        
        # 初始化游戏组件
        self.db_manager = DatabaseManager()
        self.vector_db = VectorDatabase()
        self.event_generator = EventGenerator(self.vector_db, self.db_manager)
        self.story_engine = StoryEngine(self.event_generator, self.db_manager)
        
        # 游戏状态
        self.is_initialized = False
        self.current_dialogue_round = None  # 当前对话轮次数据


class GameSessionManager:
    """游戏会话管理器（单例）"""
    _instance = None
    _sessions: Dict[str, GameSession] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameSessionManager, cls).__new__(cls)
        return cls._instance
    
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
        self._sessions[thread_id] = session
        return session
    
    def get_session(self, thread_id: str) -> Optional[GameSession]:
        """获取游戏会话"""
        return self._sessions.get(thread_id)
    
    def delete_session(self, thread_id: str):
        """删除游戏会话"""
        if thread_id in self._sessions:
            del self._sessions[thread_id]
    
    def get_all_sessions(self) -> Dict[str, GameSession]:
        """获取所有会话"""
        return self._sessions.copy()

