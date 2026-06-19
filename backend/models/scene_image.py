"""场景图片池数据库模型

注意：SceneImage 已迁移到 models/character.py 使用共享 Base。
此文件保留用于向后兼容，仅做重导出。
"""
from models.character import SceneImage

__all__ = ['SceneImage']
