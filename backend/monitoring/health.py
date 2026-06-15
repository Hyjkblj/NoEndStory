"""增强健康检查

检查系统各组件的健康状态：
- 数据库连接（PostgreSQL）
- ChromaDB 向量数据库
- LLM 提供商可达性
"""

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime

from utils.logger import setup_logger

logger = setup_logger(__name__)


class HealthChecker:
    """系统健康检查器"""
    
    def __init__(self):
        self._start_time = time.time()
    
    def check_database(self) -> Dict[str, Any]:
        """检查 PostgreSQL 数据库连接"""
        try:
            from database.db_manager import DatabaseManager
            db = DatabaseManager()
            with db.get_session() as session:
                from sqlalchemy import text
                result = session.execute(text("SELECT 1")).scalar()
            return {
                "status": "healthy" if result == 1 else "degraded",
                "message": "数据库连接正常" if result == 1 else "数据库查询异常"
            }
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "message": f"数据库连接失败: {str(e)}"
            }
    
    def check_vector_db(self) -> Dict[str, Any]:
        """检查 ChromaDB 向量数据库连接"""
        try:
            from database.vector_db import VectorDatabase
            vdb = VectorDatabase()
            # 尝试获取集合数量
            collections = vdb.client.list_collections()
            count = len(collections)
            return {
                "status": "healthy",
                "message": f"向量数据库连接正常（{count} 个集合）"
            }
        except Exception as e:
            logger.warning(f"向量数据库健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "message": f"向量数据库连接失败: {str(e)}"
            }
    
    def check_llm_provider(self) -> Dict[str, Any]:
        """检查 LLM 提供商可达性"""
        try:
            from llm import LLMService
            llm = LLMService(provider="auto")
            provider = llm.get_provider()
            model = llm.get_model()
            
            # 检查 API Key 是否配置
            from llm.config import LLMConfig
            config = LLMConfig()
            
            env_key_map = {
                "openai": "OPENAI_API_KEY",
                "volcengine": "VOLCENGINE_API_KEY",
                "dashscope": "DASHSCOPE_API_KEY",
            }
            
            api_key_configured = False
            for pname, env_var in env_key_map.items():
                provider_config = config.get_provider_config(pname) if hasattr(config, 'get_provider_config') else None
                if provider_config:
                    ak = provider_config.get("api_key", "") or provider_config.get("access_key", "")
                    if ak and ak not in ("", "your-api-key-here"):
                        api_key_configured = True
                        break
            # Fallback: check env directly
            if not api_key_configured:
                for env_var in env_key_map.values():
                    if os.getenv(env_var) and os.getenv(env_var) not in ("", "your-api-key-here"):
                        api_key_configured = True
                        break
            
            return {
                "status": "healthy" if api_key_configured else "degraded",
                "message": f"LLM 服务可用（{provider}/{model}）" if api_key_configured 
                           else "LLM API Key 未配置（文本生成功能不可用）",
                "provider": provider,
                "model": model,
            }
        except Exception as e:
            logger.warning(f"LLM 健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "message": f"LLM 服务初始化失败: {str(e)}"
            }
    
    def check_static_files(self) -> Dict[str, Any]:
        """检查静态文件目录"""
        import config
        dirs_to_check = {
            "IMAGE_SAVE_DIR": "角色图片",
            "SCENE_IMAGE_SAVE_DIR": "场景图片",
            "SMALL_SCENE_IMAGE_SAVE_DIR": "小场景图片",
            "COMPOSITE_IMAGE_SAVE_DIR": "合成图片",
        }
        
        results = {}
        for config_attr, desc in dirs_to_check.items():
            dir_config = getattr(config, config_attr, None)
            if dir_config:
                path = dir_config if os.path.isabs(dir_config) else os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), dir_config
                )
                exists = os.path.isdir(path)
                results[desc] = {
                    "path": path,
                    "exists": exists,
                    "writable": os.access(path, os.W_OK) if exists else False,
                }
            else:
                results[desc] = {"path": None, "exists": False}
        
        return results
    
    def full_check(self) -> Dict[str, Any]:
        """执行完整健康检查
        
        Returns:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "timestamp": "ISO datetime",
                "uptime_seconds": N,
                "components": {...},
                "static_files": {...}
            }
        """
        components = {
            "database": self.check_database(),
            "vector_db": self.check_vector_db(),
            "llm_provider": self.check_llm_provider(),
        }
        static_files = self.check_static_files()
        
        # 确定整体状态
        component_statuses = [c["status"] for c in components.values()]
        if "unhealthy" in component_statuses:
            overall = "unhealthy"
        elif "degraded" in component_statuses:
            overall = "degraded"
        else:
            overall = "healthy"
        
        uptime = time.time() - self._start_time
        
        return {
            "status": overall,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": round(uptime, 1),
            "version": "1.0.0",
            "components": components,
            "static_files": static_files,
        }


# 全局单例
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """获取 HealthChecker 单例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
