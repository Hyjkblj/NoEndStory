"""FastAPI应用主文件"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from api.routers import characters, game, vector_db_admin, tts, admin_stats, ws_game, admin_security
from database.db_manager import DatabaseManager
from api.exceptions import ServiceException
from api.middleware.error_handler import service_exception_handler, general_exception_handler, http_exception_handler
from api.middleware.request_logger import RequestLoggingMiddleware
from api.middleware.rate_limit import create_rate_limit_middleware
from api.middleware.cost_guard import create_cost_guard_middleware
from monitoring.token_tracker import install_token_tracking, get_token_tracker
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
app.add_exception_handler(HTTPException, http_exception_handler)
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
        # 数据库是关键服务，失败时标记为不可用并阻止应用启动
        raise RuntimeError(f"关键服务启动失败: {e}") from e
    
    # W11: 安装 Token 追踪（monkey-patch LLMService）
    try:
        install_token_tracking()
        logger.info("Token 追踪已安装")
    except Exception as e:
        logger.warning(f"Token 追踪安装失败（不影响服务）: {e}")

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

# W11: 请求日志中间件（记录所有 API 调用的耗时、状态码等）
app.add_middleware(RequestLoggingMiddleware)

# W4: 安全防护中间件（频率限制 + 成本熔断）
# 注意：FastAPI 中间件按注册的逆序执行，先注册的后执行
# 执行顺序：Request → RequestLogging → CostGuard → RateLimit → Route Handler
_excluded_paths = ["/health", "/docs", "/openapi.json", "/static", "/admin"]

app.add_middleware(
    create_rate_limit_middleware(
        default_max_requests=int(os.getenv('RATE_LIMIT_DEFAULT_MAX', '100')),
        default_window_seconds=int(os.getenv('RATE_LIMIT_WINDOW_SECONDS', '3600')),
        guest_max_plays_per_day=int(os.getenv('GUEST_FREE_PLAYS', '3')),
        excluded_paths=_excluded_paths,
    )
)

app.add_middleware(
    create_cost_guard_middleware(
        hourly_limit=float(os.getenv('COST_LIMIT_PER_IP_HOURLY', '2.0')),
        daily_limit=float(os.getenv('COST_LIMIT_PER_IP_DAILY', '5.0')),
        excluded_paths=_excluded_paths,
    )
)

# Token 额度限制：设置当前请求的客户端 IP（供 TokenTracker 使用）
@app.middleware("http")
async def set_caller_ip_for_token_tracker(request: Request, call_next):
    """将客户端 IP 传递给 TokenTracker，用于 per-IP token 额度限制"""
    from monitoring.token_tracker import TokenTracker
    client_ip = request.client.host if request.client else "unknown"
    # 支持反向代理
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    TokenTracker.set_caller_ip(client_ip)
    return await call_next(request)

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
app.include_router(admin_stats.router, prefix="/api")
app.include_router(admin_security.router)
app.include_router(ws_game.router)

# 配置静态文件服务（用于提供本地保存的图片）
# 使用 config 中的绝对路径（资源目录已在 config.py 中统一配置）

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
        static_dir = getattr(config, config_attr, None)
        if static_dir is None:
            logger.warning(f"配置项 {config_attr} 未设置，跳过 {description} 静态文件服务")
            continue

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
    audio_cache_dir = config.AUDIO_CACHE_DIR
    os.makedirs(audio_cache_dir, exist_ok=True)

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
    """健康检查（W11: 增强版 — 设置 HEALTH_FULL_CHECK=true 启用深度检查）"""
    full_check = os.getenv("HEALTH_FULL_CHECK", "false").lower() in ("true", "1", "yes")
    
    if not full_check:
        return JSONResponse(
            status_code=200,
            content={"status": "healthy", "message": "服务正常运行"}
        )
    
    # 增强健康检查：检查数据库、向量数据库、LLM 提供商
    from monitoring.health import get_health_checker
    checker = get_health_checker()
    result = checker.full_check()
    status_code = 200 if result["status"] != "unhealthy" else 503
    return JSONResponse(status_code=status_code, content=result)


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

