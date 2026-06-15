"""W3 用户认证系统：创建 game_plays 表

Revision ID: 003
Revises: 002
Create Date: 2026-06-15

变更内容：
  - game_plays 表：关联用户、thread_id、角色ID、免费标记、自动计算时长
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 game_plays 表"""
    
    # ============================================================
    # game_plays 表
    # ============================================================
    op.create_table(
        'game_plays',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('thread_id', sa.String(100), nullable=False, comment='游戏线程ID'),
        sa.Column('character_id', sa.Integer(), nullable=True, comment='角色ID'),
        sa.Column('is_free_play', sa.Boolean(), server_default='false', comment='是否为免费游玩'),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), comment='开始时间'),
        sa.Column('ended_at', sa.DateTime(), nullable=True, comment='结束时间'),
        sa.Column('duration_seconds', sa.Integer(), nullable=True, comment='游玩时长（秒）'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_game_plays_user_id', 'game_plays', ['user_id'])
    op.create_index('idx_game_plays_thread_id', 'game_plays', ['thread_id'])
    op.create_index('idx_game_plays_character_id', 'game_plays', ['character_id'])
    op.create_index('idx_game_plays_started_at', 'game_plays', ['started_at'])
    op.create_index('idx_game_plays_is_free_play', 'game_plays', ['is_free_play'])


def downgrade() -> None:
    """回滚：删除 game_plays 表"""
    op.drop_index('idx_game_plays_is_free_play', table_name='game_plays')
    op.drop_index('idx_game_plays_started_at', table_name='game_plays')
    op.drop_index('idx_game_plays_character_id', table_name='game_plays')
    op.drop_index('idx_game_plays_thread_id', table_name='game_plays')
    op.drop_index('idx_game_plays_user_id', table_name='game_plays')
    op.drop_table('game_plays')