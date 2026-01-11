"""
数据库基类和连接（PostgreSQL）
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # 连接前检查连接是否有效
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 连接池溢出大小
    echo=settings.is_debug,  # 是否打印 SQL 语句（开发环境）
)

# 创建 Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建 Base 类（用于定义模型）
Base = declarative_base()


def init_db():
    """初始化数据库（创建所有表）"""
    from app.models import database  # 导入所有模型，确保表被注册
    Base.metadata.create_all(bind=engine)
