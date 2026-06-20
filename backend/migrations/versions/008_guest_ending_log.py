"""Migration 008: 创建 guest_ending_log 表

游客结局记录表，用于每日一次结局限制。
以 IP + 日期为粒度，同一天内同一 IP 只能触发一次结局。
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
    """升级：创建 guest_ending_log 表"""
    try:
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
                WHERE table_name = 'guest_ending_log'
            )
        """)
        exists = cursor.fetchone()[0]

        if exists:
            print("[跳过] guest_ending_log 表已存在")
            return True

        # 创建 guest_ending_log 表
        cursor.execute("""
            CREATE TABLE guest_ending_log (
                id          SERIAL PRIMARY KEY,
                client_ip   VARCHAR(45)  NOT NULL,
                thread_id   VARCHAR(64)  NOT NULL UNIQUE,
                ending_type VARCHAR(32),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_key    DATE DEFAULT CURRENT_DATE
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX idx_guest_ending_ip_date
            ON guest_ending_log (client_ip, date_key)
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX idx_guest_ending_thread_id
            ON guest_ending_log (thread_id)
        """)

        print("[成功] guest_ending_log 表创建成功")
        print("[成功] 索引创建成功")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"[错误] 创建 guest_ending_log 表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def downgrade():
    """降级：删除 guest_ending_log 表"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS guest_ending_log CASCADE")

        print("[成功] guest_ending_log 表已删除")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"[错误] 删除 guest_ending_log 表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()
