"""W2 Add constraints, indexes, and new columns to existing tables

Revision ID: 001b
Revises: 001
Create Date: 2026-06-15

Changes:
  characters: ADD creator_user_id(UUID), deleted_at, 3 indexes
  character_states: ADD 12 CHECK(0-100) constraints, UNIQUE(character_id)
  character_attributes: ADD UNIQUE(character_id, attribute_type), composite index
  story_events: CREATE TABLE (Saga dual-write tracking)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001b'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- characters: new columns ----
    op.add_column('characters', sa.Column(
        'creator_user_id', postgresql.UUID(as_uuid=True), nullable=True,
        comment='Creator user ID (FK to users table, W3)'
    ))
    op.add_column('characters', sa.Column(
        'deleted_at', sa.DateTime(), nullable=True,
        comment='Soft-delete timestamp'
    ))

    # ---- characters: indexes ----
    op.create_index('idx_characters_creator_user_id', 'characters', ['creator_user_id'])
    op.create_index('idx_characters_scene_id', 'characters', ['scene_id'])
    op.create_index('idx_characters_created_at', 'characters', ['created_at'])

    # ---- character_states: CHECK constraints (0-100) ----
    for col in ['favorability', 'trust', 'hostility', 'dependence', 'emotion',
                'stress', 'anxiety', 'happiness', 'sadness', 'confidence',
                'initiative', 'caution']:
        op.execute(
            f'ALTER TABLE character_states ADD CONSTRAINT ck_{col}_range '
            f'CHECK ({col} >= 0 AND {col} <= 100)'
        )

    # ---- character_states: UNIQUE(character_id) ----
    op.create_unique_constraint(
        'uq_character_states_character_id', 'character_states', ['character_id']
    )

    # ---- character_attributes: UNIQUE + composite index ----
    op.create_unique_constraint(
        'uq_character_attributes_character_attr',
        'character_attributes',
        ['character_id', 'attribute_type']
    )
    op.create_index(
        'idx_character_attributes_character_type',
        'character_attributes',
        ['character_id', 'attribute_type']
    )

    # ---- story_events: new table ----
    op.create_table(
        'story_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(100), nullable=False,
                  comment='Event unique ID (matches ChromaDB doc_id)'),
        sa.Column('story_text', sa.Text(), nullable=False,
                  comment='Story background / narration text'),
        sa.Column('dialogue_text', sa.Text(), nullable=True,
                  comment='Dialogue text'),
        sa.Column('metadata_json', postgresql.JSON(), nullable=True,
                  comment='Event metadata'),
        sa.Column('sync_status', sa.String(20), server_default='synced',
                  comment='CDB sync status: synced/pending_sync/failed'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_story_events_character_id', 'story_events', ['character_id'])
    op.create_index('idx_story_events_sync_status', 'story_events', ['sync_status'])
    op.create_index('idx_story_events_event_id', 'story_events', ['event_id'])


def downgrade() -> None:
    # ---- story_events: drop ----
    op.drop_table('story_events')

    # ---- character_attributes: drop index + unique ----
    op.drop_index('idx_character_attributes_character_type', table_name='character_attributes')
    op.drop_constraint('uq_character_attributes_character_attr', 'character_attributes', type_='unique')

    # ---- character_states: drop unique + check constraints ----
    op.drop_constraint('uq_character_states_character_id', 'character_states', type_='unique')
    for col in ['favorability', 'trust', 'hostility', 'dependence', 'emotion',
                'stress', 'anxiety', 'happiness', 'sadness', 'confidence',
                'initiative', 'caution']:
        op.execute(f'ALTER TABLE character_states DROP CONSTRAINT IF EXISTS ck_{col}_range')

    # ---- characters: drop indexes + columns ----
    op.drop_index('idx_characters_created_at', table_name='characters')
    op.drop_index('idx_characters_scene_id', table_name='characters')
    op.drop_index('idx_characters_creator_user_id', table_name='characters')
    op.drop_column('characters', 'deleted_at')
    op.drop_column('characters', 'creator_user_id')
