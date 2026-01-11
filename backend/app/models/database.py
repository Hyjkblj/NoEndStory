"""
数据库模型（SQLAlchemy ORM）- PostgreSQL
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base
import uuid


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    threads = relationship("Thread", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class Thread(Base):
    """线程表（对应 OpenAI Thread）"""
    __tablename__ = "threads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    openai_thread_id = Column(String(255), unique=True, nullable=False, index=True)
    game_mode = Column(String(50), default="solo")  # solo | story
    character_id = Column(UUID(as_uuid=True), nullable=True)  # 选择的角色 ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="threads")
    story_state = relationship("StoryState", back_populates="thread", uselist=False, cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="thread", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Thread(id={self.id}, user_id={self.user_id}, openai_thread_id={self.openai_thread_id})>"


class StoryState(Base):
    """剧情状态表"""
    __tablename__ = "story_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    current_scene = Column(String(255), nullable=True)
    story_flags = Column(JSONB, default={}, nullable=False)  # 故事标志
    character_relations = Column(JSONB, default={}, nullable=False)  # 角色关系
    emotion_values = Column(JSONB, default={}, nullable=False)  # 情绪值
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    thread = relationship("Thread", back_populates="story_state")
    
    def __repr__(self):
        return f"<StoryState(id={self.id}, thread_id={self.thread_id}, current_scene={self.current_scene})>"


class Conversation(Base):
    """对话历史表"""
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)  # 对话内容
    meta_data = Column("metadata", JSONB, default={}, nullable=False)  # 元数据（如场景、情绪等）
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 关系
    thread = relationship("Thread", back_populates="conversations")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, thread_id={self.thread_id}, role={self.role})>"


class ImageCache(Base):
    """生成图像缓存表"""
    __tablename__ = "image_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_hash = Column(String(64), unique=True, nullable=False, index=True)
    image_url = Column(Text, nullable=False)
    prompt = Column(Text, nullable=True)  # 原始 prompt
    meta_data = Column("metadata", JSONB, default={}, nullable=False)  # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ImageCache(id={self.id}, prompt_hash={self.prompt_hash})>"
