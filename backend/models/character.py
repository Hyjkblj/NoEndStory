"""角色相关数据库模型"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, JSON, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

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
    gender = Column(String(20), nullable=False)  # 性别
    appearance = Column(Text, nullable=False)  # 外观描述（保留用于兼容）
    personality = Column(Text, nullable=False)  # 性格描述（保留用于兼容）
    scene_id = Column(String(50), default='school')  # 场景ID
    # 新增：存储完整的角色数据字典（JSON格式）
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
    attribute_type = Column(String(50), nullable=False)  # 属性类型
    attribute_value = Column(Text, nullable=False)  # 属性值
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
    favorability = Column(Float, default=0.0)  # 好感度
    trust = Column(Float, default=0.0)  # 信任度
    hostility = Column(Float, default=0.0)  # 敌意
    dependence = Column(Float, default=0.0)  # 依赖度
    emotion = Column(Float, default=50.0)  # 情绪（0-100）
    stress = Column(Float, default=0.0)  # 压力
    anxiety = Column(Float, default=0.0)  # 焦虑
    happiness = Column(Float, default=50.0)  # 快乐
    sadness = Column(Float, default=0.0)  # 悲伤
    confidence = Column(Float, default=50.0)  # 自信度
    initiative = Column(Float, default=50.0)  # 主动度
    caution = Column(Float, default=50.0)  # 谨慎度
    
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


class GameSession(Base):
    """游戏会话持久化表（W8: 会话持久化）"""
    __tablename__ = 'game_sessions'
    __table_args__ = (
        Index('idx_game_sessions_thread_id', 'thread_id', unique=True),
        Index('idx_game_sessions_user_id', 'user_id'),
        Index('idx_game_sessions_created_at', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(36), nullable=False, unique=True, comment='会话唯一ID（UUID）')
    user_id = Column(String(36), nullable=False, comment='用户ID')
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False, comment='角色ID')
    game_mode = Column(String(50), nullable=False, default='story', comment='游戏模式')
    is_initialized = Column(Integer, default=0, comment='是否已初始化: 0=否, 1=是')
    current_scene = Column(String(100), nullable=True, comment='当前场景ID')
    session_data = Column(JSON, nullable=True, comment='会话状态数据（JSON序列化）')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True, comment='会话过期时间')
    
    # 关联关系
    character = relationship('Character', foreign_keys=[character_id])


class SceneImage(Base):
    """场景图片池表

    用于存储预生成的场景图片，支持加权随机抽取和池管理。
    """
    __tablename__ = 'scene_images'
    __table_args__ = (
        Index('idx_scene_images_scene_id', 'scene_id'),
        Index('idx_scene_images_major_scene', 'major_scene_id'),
        Index('idx_scene_images_status', 'status'),
        Index('idx_scene_images_scene_status', 'scene_id', 'status'),
        CheckConstraint("status IN ('active', 'inactive', 'pending')", name='chk_scene_images_status'),
        CheckConstraint('quality_score >= 0 AND quality_score <= 5', name='chk_scene_images_quality'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    scene_id = Column(String(50), nullable=False, comment='小场景ID')
    major_scene_id = Column(String(50), nullable=True, comment='大场景ID（用于初遇场景回退）')
    image_url = Column(Text, nullable=False, comment='图片URL')
    image_path = Column(Text, nullable=True, comment='图片本地路径')
    quality_score = Column(Float, default=3.0, comment='质量分数(0-5)')
    status = Column(String(20), default='active', comment='状态: active/inactive/pending')
    use_count = Column(Integer, default=0, comment='使用次数')
    last_used_at = Column(DateTime, nullable=True, comment='最后使用时间')
    generation_time = Column(Float, nullable=True, comment='生成耗时(秒)')
    prompt_used = Column(Text, nullable=True, comment='生成时使用的prompt')
    image_metadata = Column(JSON, nullable=True, comment='扩展元数据')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'scene_id': self.scene_id,
            'major_scene_id': self.major_scene_id,
            'image_url': self.image_url,
            'image_path': self.image_path,
            'quality_score': self.quality_score,
            'status': self.status,
            'use_count': self.use_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'generation_time': self.generation_time,
            'prompt_used': self.prompt_used,
            'metadata': self.image_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<SceneImage(id={self.id}, scene_id='{self.scene_id}', quality={self.quality_score})>"


class VoiceConfig(Base):
    """角色音色配置表"""
    __tablename__ = 'voice_configs'
    __table_args__ = (
        UniqueConstraint('character_id', name='uq_voice_configs_character_id'),
        Index('idx_voice_configs_character_id', 'character_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False, unique=True, comment='角色ID')
    voice_type = Column(String(50), default='preset', comment='音色类型: preset/custom/voice_design')
    preset_voice_id = Column(String(100), nullable=True, comment='预设音色ID（如 emo_male_001）')
    voice_design_description = Column(Text, nullable=True, comment='Voice Design 描述')
    voice_params = Column(JSON, nullable=True, comment='自定义音色参数')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    character = relationship('Character', foreign_keys=[character_id])

