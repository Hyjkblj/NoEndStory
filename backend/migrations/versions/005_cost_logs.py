"""Migration 005: 创建 cost_logs 表

API调用成本记录表，用于记录每次API调用的成本，支持成本监控和统计。
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
    """升级：创建 cost_logs 表"""
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
                WHERE table_name = 'cost_logs'
            )
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("[跳过] cost_logs 表已存在")
            return True
        
        # 创建 cost_logs 表
        cursor.execute("""
            CREATE TABLE cost_logs (
                id SERIAL PRIMARY KEY,
                ip_address VARCHAR(45) NOT NULL,
                endpoint VARCHAR(200) NOT NULL,
                method VARCHAR(10) DEFAULT 'GET',
                cost_usd DECIMAL(10, 6) NOT NULL,
                tokens_used INTEGER,
                response_time_ms INTEGER,
                status_code INTEGER,
                user_agent TEXT,
                request_id VARCHAR(50),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_cost_positive CHECK (cost_usd >= 0),
                CONSTRAINT chk_tokens_positive CHECK (tokens_used >= 0)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX idx_cost_logs_ip_address ON cost_logs(ip_address)
        """)
        cursor.execute("""
            CREATE INDEX idx_cost_logs_endpoint ON cost_logs(endpoint)
        """)
        cursor.execute("""
            CREATE INDEX idx_cost_logs_created_at ON cost_logs(created_at)
        """)
        cursor.execute("""
            CREATE INDEX idx_cost_logs_ip_created ON cost_logs(ip_address, created_at)
        """)
        cursor.execute("""
            CREATE INDEX idx_cost_logs_endpoint_created ON cost_logs(endpoint, created_at)
        """)
        
        # 创建分区索引（按时间分区，提高查询性能）
        cursor.execute("""
            CREATE INDEX idx_cost_logs_created_date ON cost_logs(DATE(created_at))
        """)
        
        print("[成功] cost_logs 表创建成功")
        print("[成功] 索引创建成功")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[错误] 创建 cost_logs 表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def downgrade():
    """降级：删除 cost_logs 表"""
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
        cursor.execute("DROP TABLE IF EXISTS cost_logs CASCADE")
        
        print("[成功] cost_logs 表已删除")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[错误] 删除 cost_logs 表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()