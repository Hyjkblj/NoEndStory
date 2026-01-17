"""FastAPI应用主文件"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routers import characters, game
from database.db_manager import DatabaseManager
import uvicorn
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="无限流剧情游戏API",
    description="无限流剧情游戏后端API接口",
    version="1.0.0"
)

# 应用启动时初始化数据库
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    try:
        logger.info("正在初始化数据库...")
        db_manager = DatabaseManager()
        db_manager.init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        # 不阻止应用启动，但会记录错误

# 配置CORS（允许前端跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(characters.router, prefix="/api")
app.include_router(game.router, prefix="/api")


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
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

