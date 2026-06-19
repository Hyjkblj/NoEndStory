"""数据库模块"""

# 使用延迟导入避免循环依赖
def __getattr__(name):
    if name == 'DatabaseManager':
        from .db_manager import DatabaseManager
        return DatabaseManager
    elif name == 'VectorDatabase':
        from .vector_db import VectorDatabase
        return VectorDatabase
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['DatabaseManager', 'VectorDatabase']

