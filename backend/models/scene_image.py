"""场景图片池数据库模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class SceneImage(Base):
    """场景图片池表
    
    用于存储预生成的场景图片，支持加权随机抽取和池管理。
    """
    __tablename__ = 'scene_images'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    scene_id = Column(String(50), nullable=False, index=True)
    image_url = Column(Text, nullable=False)
    image_path = Column(Text)
    quality_score = Column(Float, default=3.0)
    status = Column(String(20), default='active', index=True)
    generation_time = Column(Float)  # 生成耗时（秒）
    prompt_used = Column(Text)  # 使用的 prompt
    image_metadata = Column(JSON)  # 扩展元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 约束
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive', 'pending')", name='chk_status'),
        CheckConstraint('quality_score >= 0 AND quality_score <= 5', name='chk_quality'),
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'scene_id': self.scene_id,
            'image_url': self.image_url,
            'image_path': self.image_path,
            'quality_score': self.quality_score,
            'status': self.status,
            'generation_time': self.generation_time,
            'prompt_used': self.prompt_used,
            'metadata': self.image_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f"<SceneImage(id={self.id}, scene_id='{self.scene_id}', quality={self.quality_score})>"