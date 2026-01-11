"""
检测数据库状态
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

print("=" * 60)
print("数据库状态检测")
print("=" * 60)
print()

# 1. 检测 PostgreSQL 数据库
print("【1】PostgreSQL 数据库状态")
print("-" * 60)

try:
    from app.database.base import engine
    from app.core.config import settings
    from sqlalchemy import inspect, text
    
    # 测试连接
    with engine.connect() as conn:
        # 检查数据库版本
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✅ 连接成功")
        print(f"   数据库版本: {version.split(',')[0]}")
        print(f"   连接 URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else settings.database_url}")
        
        # 检查表
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if tables:
            print(f"✅ 数据库表已创建 ({len(tables)} 个表):")
            expected_tables = ['users', 'threads', 'story_states', 'conversations', 'image_cache']
            for table in expected_tables:
                if table in tables:
                    # 获取表记录数
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"   ✓ {table:20s} (记录数: {count})")
                else:
                    print(f"   ✗ {table:20s} (缺失)")
            
            # 检查额外表
            extra_tables = [t for t in tables if t not in expected_tables]
            if extra_tables:
                print(f"   额外表: {', '.join(extra_tables)}")
        else:
            print("⚠️  数据库中没有表")
            
except Exception as e:
    print(f"❌ PostgreSQL 连接失败: {e}")
    print("   请检查：")
    print("   1. PostgreSQL 服务是否运行")
    print("   2. DATABASE_URL 配置是否正确")
    print("   3. 用户名和密码是否正确")

print()

# 2. 检测 Chroma 数据库
print("【2】Chroma 向量数据库状态")
print("-" * 60)

try:
    import chromadb
    from app.core.config import settings
    
    # 检查数据库路径
    db_path = settings.chroma_db_path
    abs_path = os.path.abspath(db_path)
    
    if os.path.exists(abs_path):
        print(f"✅ 数据库路径存在")
        print(f"   路径: {abs_path}")
        
        # 创建客户端并检查 Collection
        client = chromadb.PersistentClient(path=db_path)
        
        try:
            collection = client.get_collection(name="story_memories")
            count = collection.count()
            print(f"✅ Collection 已创建")
            print(f"   Collection 名称: {collection.name}")
            print(f"   当前记录数: {count}")
            print(f"   配置: 余弦相似度（cosine）")
        except Exception as e:
            print(f"⚠️  Collection 'story_memories' 不存在")
            print(f"   错误: {e}")
            print(f"   需要运行: python scripts/init_chroma.py")
    else:
        print(f"⚠️  数据库路径不存在: {abs_path}")
        print(f"   需要运行: python scripts/init_chroma.py")
        
except Exception as e:
    print(f"❌ Chroma 数据库检查失败: {e}")
    print("   请检查：")
    print("   1. chromadb 是否已安装")
    print("   2. CHROMA_DB_PATH 配置是否正确")

print()

# 3. 总结
print("=" * 60)
print("检测总结")
print("=" * 60)

try:
    # 检查 PostgreSQL
    with engine.connect() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        pg_ready = len(tables) >= 5  # 至少 5 个主要表
except:
    pg_ready = False

try:
    client = chromadb.PersistentClient(path=settings.chroma_db_path)
    collection = client.get_collection(name="story_memories")
    chroma_ready = True
except:
    chroma_ready = False

if pg_ready and chroma_ready:
    print("✅ 所有数据库已准备就绪！")
    print("   可以开始开发和测试了。")
elif pg_ready:
    print("⚠️  PostgreSQL 已就绪，但 Chroma 数据库需要初始化")
elif chroma_ready:
    print("⚠️  Chroma 已就绪，但 PostgreSQL 数据库需要初始化")
else:
    print("❌ 数据库未完全初始化，请检查上述错误信息")

print()
