"""W3 用户认证系统：创建 users 和 user_tokens 表

Revision ID: 002
Revises: 001
Create Date: 2026-06-15

变更内容：
  - users 表：UUID 主键、user_type、用户名、邮箱、密码哈希、免费次数控制
  - user_tokens 表：SHA256 哈希存储、吊销机制、刷新轮换、每用户上限 5 个
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '002'
down_revision: Union[str, None] = '001b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 users 和 user_tokens 表"""
    
    # ============================================================
    # users 表
    # ============================================================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_type', sa.String(20), nullable=False, comment='用户类型：guest | registered'),
        sa.Column('username', sa.String(50), nullable=True, comment='用户名（游客为空）'),
        sa.Column('email', sa.String(255), nullable=True, comment='邮箱（游客为空）'),
        sa.Column('password_hash', sa.String(255), nullable=True, comment='密码哈希（游客为空）'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('last_login_at', sa.DateTime(), nullable=True, comment='最后登录时间'),
        sa.Column('free_plays_remaining', sa.Integer(), server_default='0', comment='剩余免费游玩次数'),
        sa.Column('device_fingerprint', sa.String(255), nullable=True, comment='设备指纹（游客使用）'),
        sa.Column('ip_address', sa.String(45), nullable=True, comment='IP地址（游客使用）'),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_user_type', 'users', ['user_type'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    op.create_index('idx_users_last_login_at', 'users', ['last_login_at'])
    
    # 添加唯一约束（邮箱和用户名）
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_unique_constraint('uq_users_username', 'users', ['username'])
    
    # ============================================================
    # user_tokens 表
    # ============================================================
    op.create_table(
        'user_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False, comment='token的SHA256哈希'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=False, comment='过期时间'),
        sa.Column('is_revoked', sa.Boolean(), server_default='false', comment='是否已吊销'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_user_tokens_user_id', 'user_tokens', ['user_id'])
    op.create_index('idx_user_tokens_token_hash', 'user_tokens', ['token_hash'])
    op.create_index('idx_user_tokens_expires_at', 'user_tokens', ['expires_at'])
    op.create_index('idx_user_tokens_is_revoked', 'user_tokens', ['is_revoked'])
    
    # 添加唯一约束（token_hash）
    op.create_unique_constraint('uq_user_tokens_token_hash', 'user_tokens', ['token_hash'])


def downgrade() -> None:
    """回滚：删除 users 和 user_tokens 表"""
    op.drop_constraint('uq_user_tokens_token_hash', 'user_tokens', type_='unique')
    op.drop_index('idx_user_tokens_is_revoked', table_name='user_tokens')
    op.drop_index('idx_user_tokens_expires_at', table_name='user_tokens')
    op.drop_index('idx_user_tokens_token_hash', table_name='user_tokens')
    op.drop_index('idx_user_tokens_user_id', table_name='user_tokens')
    op.drop_table('user_tokens')
    
    op.drop_constraint('uq_users_username', 'users', type_='unique')
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_index('idx_users_last_login_at', table_name='users')
    op.drop_index('idx_users_created_at', table_name='users')
    op.drop_index('idx_users_user_type', table_name='users')
    op.drop_index('idx_users_username', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')