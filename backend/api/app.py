"""FastAPI应用主文件"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from api.routers import characters, game, vector_db_admin, tts
from database.db_manager import DatabaseManager
from api.exceptions import ServiceException
from api.middleware.error_handler import service_exception_handler, general_exception_handler
from utils.logger import setup_logger
import uvicorn
import os
import config

# 配置日志
logger = setup_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="无限流剧情游戏API",
    description="无限流剧情游戏后端API接口",
    version="1.0.0"
)

# 注册异常处理器
app.add_exception_handler(ServiceException, service_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 应用启动时初始化数据库
@app.on_event("startup")
async def startup_event():
    """应用启动时执行（W8: 关键服务失败返回503）"""
    global _startup_failed
    _startup_failed = False
    
    try:
        logger.info("正在初始化数据库...")
        db_manager = DatabaseManager()
        db_manager.init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}", exc_info=True)
        _startup_failed = True
        # 数据库是关键服务，失败时标记为不可用

# 全局变量标记启动是否失败
_startup_failed = False

# 配置CORS（允许前端跨域请求）
# 根据环境变量配置允许的来源（安全最佳实践）
_env = os.getenv('ENV', 'dev')
if _env == 'prod':
    # 生产环境：只允许指定的前端域名
    allowed_origins_str = os.getenv('ALLOWED_ORIGINS', '')
    if not allowed_origins_str:
        raise ValueError("生产环境必须设置 ALLOWED_ORIGINS 环境变量（逗号分隔的前端域名列表）")
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers = ["Content-Type", "Authorization", "X-Requested-With"]
else:
    # 开发环境：允许本地开发服务器
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    # 如果设置了ALLOWED_ORIGINS，也添加到允许列表
    if os.getenv('ALLOWED_ORIGINS'):
        allowed_origins.extend([origin.strip() for origin in os.getenv('ALLOWED_ORIGINS').split(',')])
    allowed_methods = ["*"]
    allowed_headers = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # ✅ 只允许指定来源
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
)

# W8: 启动失败时返回503的中间件
@app.middleware("http")
async def check_startup_status(request: Request, call_next):
    """检查应用启动状态，如果关键服务失败则返回503"""
    global _startup_failed
    
    # 健康检查端点允许访问
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    # 如果启动失败，返回503
    if _startup_failed:
        return JSONResponse(
            status_code=503,
            content={
                "code": 503,
                "message": "服务暂时不可用，关键服务启动失败",
                "data": None
            }
        )
    
    return await call_next(request)

# 注册路由
app.include_router(characters.router, prefix="/api")
app.include_router(game.router, prefix="/api")
app.include_router(vector_db_admin.router, prefix="/api")
app.include_router(tts.router, prefix="/api")

# 配置静态文件服务（用于提供本地保存的图片）- W8: 合并为循环，消除重复代码
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 静态文件挂载配置列表（路径映射）
STATIC_MOUNTS = [
    # (URL路径, 配置属性名, 描述)
    ("/static/images/characters", "IMAGE_SAVE_DIR", "角色图片"),
    ("/static/images/scenes", "SCENE_IMAGE_SAVE_DIR", "场景图片"),
    ("/static/images/smallscenes", "SMALL_SCENE_IMAGE_SAVE_DIR", "小场景图片"),
    ("/static/images/composite", "COMPOSITE_IMAGE_SAVE_DIR", "合成图片"),
]

# 挂载图片静态文件服务
for mount_path, config_attr, description in STATIC_MOUNTS:
    try:
        dir_config = getattr(config, config_attr, None)
        if dir_config is None:
            logger.warning(f"配置项 {config_attr} 未设置，跳过 {description} 静态文件服务")
            continue
        
        # 解析目录路径（支持绝对路径和相对路径）
        if os.path.isabs(dir_config):
            static_dir = dir_config
        else:
            static_dir = os.path.join(backend_dir, dir_config)
        
        # 确保目录存在
        os.makedirs(static_dir, exist_ok=True)
        
        # 生成唯一的名称（基于URL路径）
        name = mount_path.replace("/", "_").strip("_")
        
        # 挂载静态文件服务
        app.mount(mount_path, StaticFiles(directory=static_dir), name=name)
        logger.info(f"{description}静态文件服务已配置: {static_dir} -> {mount_path}")
    except Exception as e:
        logger.warning(f"配置{description}静态文件服务失败: {e}，本地图片将无法通过URL访问")

# 配置音频文件静态文件服务（TTS缓存）
try:
    audio_cache_dir = os.path.join(backend_dir, "audio", "cache")
    os.makedirs(audio_cache_dir, exist_ok=True)
    
    # 挂载音频文件静态文件服务
    # 访问路径：/static/audio/cache/{filename}
    app.mount("/static/audio/cache", StaticFiles(directory=audio_cache_dir), name="audio_cache")
    logger.info(f"音频缓存静态文件服务已配置: {audio_cache_dir} -> /static/audio/cache")
except Exception as e:
    logger.warning(f"配置音频缓存静态文件服务失败: {e}")

# 配置管理页面静态文件服务
try:
    admin_dir = os.path.join(backend_dir, "static", "admin")
    os.makedirs(admin_dir, exist_ok=True)
    
    # 挂载管理页面静态文件服务
    app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")
    logger.info(f"管理页面静态文件服务已配置: {admin_dir} -> /admin")
except Exception as e:
    logger.warning(f"配置管理页面静态文件服务失败: {e}")


@app.get("/health")
async def check_server_health():
    """健康检查"""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "message": "服务正常运行"}
    )


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "无限流剧情游戏API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    # 确保工作目录是backend目录，这样相对路径才能正确解析
    import os
    # __file__ 是 api/app.py，需要回到backend目录
    api_dir = os.path.dirname(os.path.abspath(__file__))  # backend/api
    backend_dir = os.path.dirname(api_dir)  # backend
    os.chdir(backend_dir)
    logger.info(f"API服务工作目录: {os.getcwd()}")
    
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

