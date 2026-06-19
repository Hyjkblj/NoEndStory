"""创建 scene_images 表

Revision ID: 004
Revises: 003
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'scene_images',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('scene_id', sa.String(50), nullable=False, comment='场景ID'),
        sa.Column('image_url', sa.Text(), nullable=False, comment='图片URL'),
        sa.Column('image_path', sa.Text(), nullable=True, comment='图片本地路径'),
        sa.Column('quality_score', sa.Float(), server_default='3.0', comment='质量分数(0-5)'),
        sa.Column('status', sa.String(20), server_default='active', comment='状态: active/inactive/pending'),
        sa.Column('use_count', sa.Integer(), server_default='0', comment='使用次数'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True, comment='最后使用时间'),
        sa.Column('generation_time', sa.Float(), nullable=True, comment='生成耗时(秒)'),
        sa.Column('prompt_used', sa.Text(), nullable=True, comment='生成时使用的prompt'),
        sa.Column('image_metadata', sa.JSON(), nullable=True, comment='扩展元数据'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('active', 'inactive', 'pending')", name='chk_scene_images_status'),
        sa.CheckConstraint('quality_score >= 0 AND quality_score <= 5', name='chk_scene_images_quality'),
    )

    # 创建索引
    op.create_index('idx_scene_images_scene_id', 'scene_images', ['scene_id'])
    op.create_index('idx_scene_images_status', 'scene_images', ['status'])
    op.create_index('idx_scene_images_scene_status', 'scene_images', ['scene_id', 'status'])


def downgrade():
    op.drop_index('idx_scene_images_scene_status', table_name='scene_images')
    op.drop_index('idx_scene_images_status', table_name='scene_images')
    op.drop_index('idx_scene_images_scene_id', table_name='scene_images')
    op.drop_table('scene_images')
