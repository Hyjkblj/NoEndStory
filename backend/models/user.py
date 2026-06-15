"""用户相关数据库模型"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, JSON, Boolean, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

# 导入现有的Base
from models.character import Base


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_username', 'username'),
        Index('idx_users_user_type', 'user_type'),
        Index('idx_users_created_at', 'created_at'),
        Index('idx_users_last_login_at', 'last_login_at'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_type = Column(String(20), nullable=False, comment='用户类型：guest | registered')
    username = Column(String(50), nullable=True, comment='用户名（游客为空）')
    email = Column(String(255), nullable=True, comment='邮箱（游客为空）')
    password_hash = Column(String(255), nullable=True, comment='密码哈希（游客为空）')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    last_login_at = Column(DateTime, nullable=True, comment='最后登录时间')
    free_plays_remaining = Column(Integer, default=0, comment='剩余免费游玩次数')
    device_fingerprint = Column(String(255), nullable=True, comment='设备指纹（游客使用）')
    ip_address = Column(String(45), nullable=True, comment='IP地址（游客使用）')
    
    # 关联关系
    tokens = relationship('UserToken', back_populates='user', cascade='all, delete-orphan')
    game_plays = relationship('GamePlay', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<User(id={self.id}, type={self.user_type}, username={self.username})>"


class UserToken(Base):
    """用户token表"""
    __tablename__ = 'user_tokens'
    __table_args__ = (
        Index('idx_user_tokens_user_id', 'user_id'),
        Index('idx_user_tokens_token_hash', 'token_hash'),
        Index('idx_user_tokens_expires_at', 'expires_at'),
        Index('idx_user_tokens_is_revoked', 'is_revoked'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    token_hash = Column(String(64), nullable=False, comment='token的SHA256哈希')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    expires_at = Column(DateTime, nullable=False, comment='过期时间')
    is_revoked = Column(Boolean, default=False, comment='是否已吊销')
    
    # 关联关系
    user = relationship('User', back_populates='tokens')
    
    def __repr__(self):
        return f"<UserToken(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"


class GamePlay(Base):
    """游戏游玩记录表"""
    __tablename__ = 'game_plays'
    __table_args__ = (
        Index('idx_game_plays_user_id', 'user_id'),
        Index('idx_game_plays_thread_id', 'thread_id'),
        Index('idx_game_plays_character_id', 'character_id'),
        Index('idx_game_plays_started_at', 'started_at'),
        Index('idx_game_plays_is_free_play', 'is_free_play'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    thread_id = Column(String(100), nullable=False, comment='游戏线程ID')
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=True, comment='角色ID')
    is_free_play = Column(Boolean, default=False, comment='是否为免费游玩')
    started_at = Column(DateTime, default=datetime.utcnow, comment='开始时间')
    ended_at = Column(DateTime, nullable=True, comment='结束时间')
    duration_seconds = Column(Integer, nullable=True, comment='游玩时长（秒）')
    
    # 关联关系
    user = relationship('User', back_populates='game_plays')
    character = relationship('Character')
    
    def __repr__(self):
        return f"<GamePlay(id={self.id}, user_id={self.user_id}, thread_id={self.thread_id})>"