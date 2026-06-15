"""Migration 006: 创建 audit_logs 表

审计日志表，用于记录系统安全事件和操作审计，支持安全分析和合规要求。
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
    """升级：创建 audit_logs 表"""
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
                WHERE table_name = 'audit_logs'
            )
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("[跳过] audit_logs 表已存在")
            return True
        
        # 创建 audit_logs 表
        cursor.execute("""
            CREATE TABLE audit_logs (
                id SERIAL PRIMARY KEY,
                action VARCHAR(50) NOT NULL,
                entity_type VARCHAR(50),
                entity_id VARCHAR(100),
                ip_address VARCHAR(45),
                user_id VARCHAR(100),
                username VARCHAR(100),
                old_value JSONB,
                new_value JSONB,
                details JSONB,
                status VARCHAR(20) DEFAULT 'success',
                error_message TEXT,
                request_id VARCHAR(50),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_action CHECK (action IN (
                    'ip_banned', 'ip_unbanned', 'user_login', 'user_logout',
                    'user_register', 'guest_created', 'game_started', 'game_ended',
                    'api_call', 'error', 'security_event', 'admin_action'
                )),
                CONSTRAINT chk_status CHECK (status IN ('success', 'failure', 'warning'))
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX idx_audit_logs_action ON audit_logs(action)
        """)
        cursor.execute("""
            CREATE INDEX idx_audit_logs_entity_type ON audit_logs(entity_type)
        """)
        cursor.execute("""
            CREATE INDEX idx_audit_logs_ip_address ON audit_logs(ip_address)
        """)
        cursor.execute("""
            CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id)
        """)
        cursor.execute("""
            CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at)
        """)
        cursor.execute("""
            CREATE INDEX idx_audit_logs_action_created ON audit_logs(action, created_at)
        """)
        cursor.execute("""
            CREATE INDEX idx_audit_logs_entity_created ON audit_logs(entity_type, entity_id, created_at)
        """)
        
        # 创建GIN索引用于JSONB查询
        cursor.execute("""
            CREATE INDEX idx_audit_logs_details_gin ON audit_logs USING GIN (details)
        """)
        cursor.execute("""
            CREATE INDEX idx_audit_logs_old_value_gin ON audit_logs USING GIN (old_value)
        """)
        cursor.execute("""
            CREATE INDEX idx_audit_logs_new_value_gin ON audit_logs USING GIN (new_value)
        """)
        
        print("[成功] audit_logs 表创建成功")
        print("[成功] 索引创建成功")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[错误] 创建 audit_logs 表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def downgrade():
    """降级：删除 audit_logs 表"""
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
        cursor.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
        
        print("[成功] audit_logs 表已删除")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[错误] 删除 audit_logs 表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()