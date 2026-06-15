"""Migration 007: 创建 scene_images 表

场景图片池表，用于存储预生成的场景图片，支持加权随机抽取和池管理。
"""
import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'noendstory'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


def upgrade():
    """升级：创建 scene_images 表"""
    try:
        # 连接到数据库
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 检查表是否已存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'scene_images'
            )
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("[跳过] scene_images 表已存在")
            return True
        
        # 创建 scene_images 表
        cursor.execute("""
            CREATE TABLE scene_images (
                id SERIAL PRIMARY KEY,
                scene_id VARCHAR(50) NOT NULL,
                image_url TEXT NOT NULL,
                image_path TEXT,
                quality_score FLOAT DEFAULT 3.0,
                status VARCHAR(20) DEFAULT 'active',
                generation_time FLOAT,
                prompt_used TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_status CHECK (status IN ('active', 'inactive', 'pending')),
                CONSTRAINT chk_quality CHECK (quality_score >= 0 AND quality_score <= 5)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX idx_scene_images_scene_id ON scene_images(scene_id)
        """)
        cursor.execute("""
            CREATE INDEX idx_scene_images_status ON scene_images(status)
        """)
        cursor.execute("""
            CREATE INDEX idx_scene_images_quality ON scene_images(quality_score)
        """)
        cursor.execute("""
            CREATE INDEX idx_scene_images_scene_status ON scene_images(scene_id, status)
        """)
        
        print("[成功] scene_images 表创建成功")
        print("[成功] 索引创建成功")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[错误] 创建 scene_images 表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def downgrade():
    """降级：删除 scene_images 表"""
    try:
        # 连接到数据库
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 删除表
        cursor.execute("DROP TABLE IF EXISTS scene_images CASCADE")
        
        print("[成功] scene_images 表已删除")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[错误] 删除 scene_images 表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()