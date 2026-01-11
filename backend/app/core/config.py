"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = "No End Story API"
    app_version: str = "0.1.0"
    app_env: str = "development"  # development | production
    app_secret_key: str = "your-secret-key-change-in-production"
    debug: bool = True
    
    @property
    def is_debug(self) -> bool:
        """是否为调试模式"""
        return self.debug and self.app_env == "development"
    
    # PostgreSQL 数据库配置（结构化数据）
    database_url: str = "postgresql://user:password@localhost/noendstory"
    
    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"
    
    # OpenAI 配置
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_image_model: str = "dall-e-3"
    openai_embedding_model: str = "text-embedding-3-large"
    
    # Assistant IDs（在初始化时创建）
    director_assistant_id: Optional[str] = None
    writer_assistant_id: Optional[str] = None
    
    # Chroma 配置（向量数据库 - 本地部署）
    chroma_db_path: str = "./chroma_db"
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 创建全局配置实例
settings = Settings()
