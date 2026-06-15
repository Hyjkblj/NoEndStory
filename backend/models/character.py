"""角色相关数据库模型"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, JSON, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Character(Base):
    """角色主表"""
    __tablename__ = 'characters'
    __table_args__ = (
        Index('idx_characters_creator_user_id', 'creator_user_id'),
        Index('idx_characters_scene_id', 'scene_id'),
        Index('idx_characters_created_at', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    gender = Column(String(20), nullable=False)
    appearance = Column(Text, nullable=False)
    personality = Column(Text, nullable=False)
    scene_id = Column(String(50), default='school')
    character_data = Column(JSON, nullable=True, comment='完整的角色数据字典，包含外观、性格、年龄、体重等所有前端数据')
    # W2 新增字段
    creator_user_id = Column(UUID(as_uuid=True), nullable=True, comment='创建者用户ID（关联users表，W3实现）')
    deleted_at = Column(DateTime, nullable=True, comment='软删除时间戳')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    attributes = relationship('CharacterAttribute', back_populates='character', cascade='all, delete-orphan')
    states = relationship('CharacterState', back_populates='character', cascade='all, delete-orphan')


class CharacterAttribute(Base):
    """角色决定因素表"""
    __tablename__ = 'character_attributes'
    __table_args__ = (
        UniqueConstraint('character_id', 'attribute_type', name='uq_character_attributes_character_attr'),
        Index('idx_character_attributes_character_type', 'character_id', 'attribute_type'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    attribute_type = Column(String(50), nullable=False)
    attribute_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    character = relationship('Character', back_populates='attributes')


class CharacterState(Base):
    """角色状态值表"""
    __tablename__ = 'character_states'
    __table_args__ = (
        UniqueConstraint('character_id', name='uq_character_states_character_id'),
        CheckConstraint('favorability >= 0 AND favorability <= 100', name='ck_favorability_range'),
        CheckConstraint('trust >= 0 AND trust <= 100', name='ck_trust_range'),
        CheckConstraint('hostility >= 0 AND hostility <= 100', name='ck_hostility_range'),
        CheckConstraint('dependence >= 0 AND dependence <= 100', name='ck_dependence_range'),
        CheckConstraint('emotion >= 0 AND emotion <= 100', name='ck_emotion_range'),
        CheckConstraint('stress >= 0 AND stress <= 100', name='ck_stress_range'),
        CheckConstraint('anxiety >= 0 AND anxiety <= 100', name='ck_anxiety_range'),
        CheckConstraint('happiness >= 0 AND happiness <= 100', name='ck_happiness_range'),
        CheckConstraint('sadness >= 0 AND sadness <= 100', name='ck_sadness_range'),
        CheckConstraint('confidence >= 0 AND confidence <= 100', name='ck_confidence_range'),
        CheckConstraint('initiative >= 0 AND initiative <= 100', name='ck_initiative_range'),
        CheckConstraint('caution >= 0 AND caution <= 100', name='ck_caution_range'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    
    # 状态值
    favorability = Column(Float, default=0.0)
    trust = Column(Float, default=0.0)
    hostility = Column(Float, default=0.0)
    dependence = Column(Float, default=0.0)
    emotion = Column(Float, default=50.0)
    stress = Column(Float, default=0.0)
    anxiety = Column(Float, default=0.0)
    happiness = Column(Float, default=50.0)
    sadness = Column(Float, default=0.0)
    confidence = Column(Float, default=50.0)
    initiative = Column(Float, default=50.0)
    caution = Column(Float, default=50.0)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    character = relationship('Character', back_populates='states')


class StoryEvent(Base):
    """故事事件追踪表（Saga 双写补偿：PG 主写，CDB 副写）"""
    __tablename__ = 'story_events'
    __table_args__ = (
        Index('idx_story_events_character_id', 'character_id'),
        Index('idx_story_events_sync_status', 'sync_status'),
        Index('idx_story_events_event_id', 'event_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    event_id = Column(String(100), nullable=False, comment='事件唯一ID（对应 ChromaDB 中的 doc_id）')
    story_text = Column(Text, nullable=False, comment='故事背景/旁白文本')
    dialogue_text = Column(Text, nullable=True, comment='对话文本')
    metadata_json = Column(JSON, nullable=True, comment='事件元数据')
    sync_status = Column(String(20), default='synced', comment='CDB 同步状态: synced / pending_sync / failed')
    created_at = Column(DateTime, default=datetime.utcnow)
