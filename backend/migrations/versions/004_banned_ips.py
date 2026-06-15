"""Migration 004: 创建 banned_ips 表

IP封禁表，用于存储被封禁的IP地址，支持过期封禁和永久封禁。
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
    """升级：创建 banned_ips 表"""
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
                WHERE table_name = 'banned_ips'
            )
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("[跳过] banned_ips 表已存在")
            return True
        
        # 创建 banned_ips 表
        cursor.execute("""
            CREATE TABLE banned_ips (
                id SERIAL PRIMARY KEY,
                ip_address VARCHAR(45) NOT NULL,
                reason TEXT NOT NULL,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                banned_until TIMESTAMP,
                permanent BOOLEAN DEFAULT FALSE,
                banned_by VARCHAR(100) DEFAULT 'system',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_ip_format CHECK (
                    ip_address ~ '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$' OR
                    ip_address ~ '^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
                )
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX idx_banned_ips_ip_address ON banned_ips(ip_address)
        """)
        cursor.execute("""
            CREATE INDEX idx_banned_ips_is_active ON banned_ips(is_active)
        """)
        cursor.execute("""
            CREATE INDEX idx_banned_ips_banned_until ON banned_ips(banned_until)
        """)
        cursor.execute("""
            CREATE INDEX idx_banned_ips_active_ip ON banned_ips(ip_address, is_active)
        """)
        
        # 创建唯一约束：每个IP只有一条活跃的封禁记录
        cursor.execute("""
            CREATE UNIQUE INDEX idx_banned_ips_unique_active 
            ON banned_ips(ip_address) 
            WHERE is_active = TRUE
        """)
        
        print("[成功] banned_ips 表创建成功")
        print("[成功] 索引创建成功")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[错误] 创建 banned_ips 表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def downgrade():
    """降级：删除 banned_ips 表"""
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
        cursor.execute("DROP TABLE IF EXISTS banned_ips CASCADE")
        
        print("[成功] banned_ips 表已删除")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[错误] 删除 banned_ips 表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()