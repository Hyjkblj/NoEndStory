"""
初始化 PostgreSQL 数据库
"""
import sys
import os
from pathlib import Path

# 设置 UTF-8 编码（Windows 控制台支持）
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="replace")

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# 切换到 backend 目录，确保 .env 文件能被正确读取
os.chdir(backend_dir)

from app.database.base import init_db, engine
from app.core.config import settings


def create_database():
    """创建数据库表"""
    print(f"正在连接数据库: {settings.database_url.split('@')[1] if '@' in settings.database_url else settings.database_url}")
    print("创建数据库表...")
    
    try:
        init_db()
        print("✅ PostgreSQL 数据库表创建成功！")
        print(f"   数据库 URL: {settings.database_url}")
        print("\n创建的表:")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        for table in tables:
            print(f"   - {table}")
    except Exception as e:
        import traceback
        print(f"❌ 数据库初始化失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   详细错误: {str(e)}")
        print("\n完整错误堆栈:")
        traceback.print_exc()
        print("\n请检查：")
        print("1. PostgreSQL 是否已安装并运行")
        print("2. 数据库是否存在（如：noendstory）")
        print("3. DATABASE_URL 配置是否正确")
        print(f"4. 当前 DATABASE_URL: {settings.database_url}")
        sys.exit(1)


if __name__ == "__main__":
    create_database()
