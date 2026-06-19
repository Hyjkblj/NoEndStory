"""数据库模型和大模型服务"""
from .character import Character, CharacterAttribute, CharacterState, StoryEvent, GameSession, VoiceConfig, SceneImage

# 延迟导入避免循环依赖
def __getattr__(name):
    if name == 'TextModelService':
        from .text_model_service import TextModelService
        return TextModelService
    elif name == 'ImageModelService':
        from .image_model_service import ImageModelService
        return ImageModelService
    elif name == 'VoiceModelService':
        from .voice_model_service import VoiceModelService
        return VoiceModelService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# W9a: TextModelService 已合并到 TextGenerationService（game/ai_generator.py）
# 保留 TextModelService 作为兼容别名

__all__ = [
    # 数据库模型
    'Character',
    'CharacterAttribute',
    'CharacterState',
    'StoryEvent',
    'GameSession',
    'VoiceConfig',
    'SceneImage',
    # 大模型服务
    'TextModelService',
    'ImageModelService',
    'VoiceModelService',
]

