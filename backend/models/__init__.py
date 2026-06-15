"""数据库模型和大模型服务"""
from .character import Character, CharacterAttribute, CharacterState, StoryEvent
from .text_model_service import TextModelService  # 保留兼容，已合并到 TextGenerationService
from .image_model_service import ImageModelService
from .voice_model_service import VoiceModelService

# W9a: TextModelService 已合并到 TextGenerationService（game/ai_generator.py）
# 保留 TextModelService 作为兼容别名

__all__ = [
    # 数据库模型
    'Character', 
    'CharacterAttribute', 
    'CharacterState',
    'StoryEvent',
    # 大模型服务
    'TextModelService',
    'ImageModelService',
    'VoiceModelService',
]

