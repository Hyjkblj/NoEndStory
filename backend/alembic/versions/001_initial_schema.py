"""W2 Initial Schema: base tables (matching pre-W2 database state)

Revision ID: 001
Revises: None
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'characters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('gender', sa.String(20), nullable=False),
        sa.Column('appearance', sa.Text(), nullable=False),
        sa.Column('personality', sa.Text(), nullable=False),
        sa.Column('scene_id', sa.String(50), server_default='school'),
        sa.Column('character_data', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'character_states',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('favorability', sa.Float(), server_default='0'),
        sa.Column('trust', sa.Float(), server_default='0'),
        sa.Column('hostility', sa.Float(), server_default='0'),
        sa.Column('dependence', sa.Float(), server_default='0'),
        sa.Column('emotion', sa.Float(), server_default='50'),
        sa.Column('stress', sa.Float(), server_default='0'),
        sa.Column('anxiety', sa.Float(), server_default='0'),
        sa.Column('happiness', sa.Float(), server_default='50'),
        sa.Column('sadness', sa.Float(), server_default='0'),
        sa.Column('confidence', sa.Float(), server_default='50'),
        sa.Column('initiative', sa.Float(), server_default='50'),
        sa.Column('caution', sa.Float(), server_default='50'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
    )
    op.create_table(
        'character_attributes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('attribute_type', sa.String(50), nullable=False),
        sa.Column('attribute_value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
    )


def downgrade() -> None:
    op.drop_table('character_attributes')
    op.drop_table('character_states')
    op.drop_table('characters')
