"""统一日志系统（W9a: 统一级别和格式）"""
import logging
import sys
import os
from typing import Optional

# 尝试导入jsonlogger（可选）
try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False

# 默认日志级别（环境变量 LOG_LEVEL 控制，默认 INFO）
_DEFAULT_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
# 默认日志格式
_DEFAULT_FORMAT = '[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s'
_DEFAULT_DATEFMT = '%Y-%m-%d %H:%M:%S'

# 模块级缓存：已配置的 logger 名称集合
_configured_loggers: set = set()


def setup_logger(
    name: str,
    level: Optional[str] = None,
    use_json: bool = False
) -> logging.Logger:
    """设置结构化日志
    
    Args:
        name: 日志器名称（通常是 __name__）
        level: 日志级别（DEBUG/INFO/WARNING/ERROR），如果为None则从环境变量 LOG_LEVEL 读取
        use_json: 是否使用JSON格式（生产环境推荐）
        
    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回（避免重复添加 handler）
    if name in _configured_loggers:
        return logger
    
    # 确定日志级别
    if level is None:
        resolved_level = _DEFAULT_LEVEL
    else:
        resolved_level = level.upper()
    
    numeric_level = getattr(logging, resolved_level, logging.INFO)
    logger.setLevel(numeric_level)
    
    # 防止传播到 root logger 造成重复输出
    logger.propagate = False
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # 选择格式化器
    if use_json and JSON_LOGGER_AVAILABLE:
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt=_DEFAULT_DATEFMT
        )
    else:
        formatter = logging.Formatter(
            _DEFAULT_FORMAT,
            datefmt=_DEFAULT_DATEFMT
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    _configured_loggers.add(name)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """获取日志器（便捷方法）
    
    Args:
        name: 日志器名称（通常是 __name__）
        
    Returns:
        Logger实例
    """
    return setup_logger(name)
