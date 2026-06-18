"""FastAPI依赖注入定义"""
from typing import Optional
from api.services.game_service import GameService
from api.services.character_service import CharacterService
from api.services.image_service import ImageService
from api.services.tts_service import TTSService
from api.services.game_session import GameSessionManager
from utils.logger import get_logger

logger = get_logger(__name__)

# Service实例缓存（用于单例模式，但通过依赖注入管理）
_game_service: Optional[GameService] = None
_character_service: Optional[CharacterService] = None
_image_service: Optional[ImageService] = None
_tts_service: Optional[TTSService] = None
_session_manager: Optional[GameSessionManager] = None
_redis_client = None


def get_redis_client():
    """获取Redis客户端实例（单例模式）"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            import config
            _redis_client = redis.Redis(**config.REDIS_CONFIG)
            # 测试连接
            _redis_client.ping()
            logger.info(f"Redis 连接成功: {config.REDIS_CONFIG['host']}:{config.REDIS_CONFIG['port']}")
        except ImportError:
            logger.warning("redis 未安装，短期记忆将使用内存存储")
            _redis_client = None
        except Exception as e:
            logger.warning(f"Redis 连接失败: {e}，短期记忆将使用内存存储")
            _redis_client = None
    return _redis_client


def get_image_service() -> ImageService:
    """获取ImageService实例（单例模式，但通过依赖注入管理）"""
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service


def get_character_service() -> CharacterService:
    """获取CharacterService实例（单例模式，但通过依赖注入管理）"""
    global _character_service
    if _character_service is None:
        image_service = get_image_service()
        _character_service = CharacterService(image_service=image_service)
    return _character_service


def get_game_service() -> GameService:
    """获取GameService实例（单例模式，但通过依赖注入管理）"""
    global _game_service
    if _game_service is None:
        image_service = get_image_service()
        character_service = get_character_service()
        _game_service = GameService(
            character_service=character_service,
            image_service=image_service
        )
    return _game_service


def get_tts_service() -> TTSService:
    """获取TTSService实例（单例模式，但通过依赖注入管理）"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service


def get_session_manager() -> GameSessionManager:
    """获取GameSessionManager实例（单例模式，但通过依赖注入管理）"""
    global _session_manager
    if _session_manager is None:
        _session_manager = GameSessionManager()
    return _session_manager
