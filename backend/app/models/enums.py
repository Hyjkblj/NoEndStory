"""
枚举类型定义
"""
from enum import Enum


class GameMode(str, Enum):
    """游戏模式"""
    SOLO = "solo"  # 单人模式
    STORY = "story"  # 故事模式


class ConversationRole(str, Enum):
    """对话角色"""
    USER = "user"  # 用户
    ASSISTANT = "assistant"  # AI 助手


class ImageQuality(str, Enum):
    """图像质量"""
    STANDARD = "standard"  # 标准质量
    HD = "hd"  # 高清质量
