"""Manually apply W2 schema changes"""
from sqlalchemy import create_engine, text
e = create_engine('postgresql://postgres:000000@localhost:5432/noendstory')
conn = e.connect()

print("=== Applying W2 changes ===")

# 1. characters: new columns
print("Adding creator_user_id to characters...")
try:
    conn.execute(text("ALTER TABLE characters ADD COLUMN creator_user_id UUID"))
    print("  OK")
except Exception as ex:
    print(f"  SKIP: {ex}")

print("Adding deleted_at to characters...")
try:
    conn.execute(text("ALTER TABLE characters ADD COLUMN deleted_at TIMESTAMP"))
    print("  OK")
except Exception as ex:
    print(f"  SKIP: {ex}")

# 2. characters: indexes
for idx_name, idx_col in [
    ('idx_characters_creator_user_id', 'creator_user_id'),
    ('idx_characters_scene_id', 'scene_id'),
    ('idx_characters_created_at', 'created_at'),
]:
    print(f"Creating index {idx_name}...")
    try:
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON characters ({idx_col})"))
        print("  OK")
    except Exception as ex:
        print(f"  SKIP: {ex}")

# 3. character_states: CHECK constraints
for col in ['favorability', 'trust', 'hostility', 'dependence', 'emotion',
            'stress', 'anxiety', 'happiness', 'sadness', 'confidence',
            'initiative', 'caution']:
    cname = f'ck_{col}_range'
    print(f"Adding CHECK {cname}...")
    try:
        conn.execute(text(
            f"ALTER TABLE character_states ADD CONSTRAINT {cname} "
            f"CHECK ({col} >= 0 AND {col} <= 100)"
        ))
        print("  OK")
    except Exception as ex:
        print(f"  SKIP: {ex}")

# 4. character_states: UNIQUE(character_id)
print("Adding UNIQUE character_states.character_id...")
try:
    conn.execute(text(
        "ALTER TABLE character_states ADD CONSTRAINT uq_character_states_character_id UNIQUE (character_id)"
    ))
    print("  OK")
except Exception as ex:
    print(f"  SKIP: {ex}")

# 5. character_attributes: UNIQUE + index
print("Adding UNIQUE character_attributes.(character_id, attribute_type)...")
try:
    conn.execute(text(
        "ALTER TABLE character_attributes ADD CONSTRAINT uq_character_attributes_character_attr "
        "UNIQUE (character_id, attribute_type)"
    ))
    print("  OK")
except Exception as ex:
    print(f"  SKIP: {ex}")

print("Creating index idx_character_attributes_character_type...")
try:
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS idx_character_attributes_character_type "
        "ON character_attributes (character_id, attribute_type)"
    ))
    print("  OK")
except Exception as ex:
    print(f"  SKIP: {ex}")

# 6. story_events: new table
print("Creating story_events table...")
try:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS story_events (
            id SERIAL PRIMARY KEY,
            character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
            event_id VARCHAR(100) NOT NULL,
            story_text TEXT NOT NULL,
            dialogue_text TEXT,
            metadata_json JSONB,
            sync_status VARCHAR(20) DEFAULT 'synced',
            created_at TIMESTAMP DEFAULT now()
        )
    """))
    print("  OK")
except Exception as ex:
    print(f"  SKIP: {ex}")

# 7. story_events: indexes
for idx_name, idx_col in [
    ('idx_story_events_character_id', 'character_id'),
    ('idx_story_events_sync_status', 'sync_status'),
    ('idx_story_events_event_id', 'event_id'),
]:
    print(f"Creating index {idx_name}...")
    try:
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON story_events ({idx_col})"))
        print("  OK")
    except Exception as ex:
        print(f"  SKIP: {ex}")

conn.commit()
conn.close()
print("\n=== W2 changes applied ===")
