"""Check W2 schema changes specifically"""
from sqlalchemy import create_engine, text
e = create_engine('postgresql://postgres:000000@localhost:5432/noendstory')
conn = e.connect()

# Check characters new columns
print("=== characters columns (W2) ===")
r = conn.execute(text("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'characters'
    ORDER BY ordinal_position
"""))
for row in r: print(f"  {row[0]:30s} {row[1]:20s} null={row[2]}")

# Check character_states constraints
print("\n=== character_states CHECK constraints ===")
r = conn.execute(text("""
    SELECT conname, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'character_states'::regclass AND contype = 'c'
"""))
for row in r: print(f"  {row[0]}: {row[1]}")

# Check character_states UNIQUE
print("\n=== character_states UNIQUE constraints ===")
r = conn.execute(text("""
    SELECT conname, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'character_states'::regclass AND contype = 'u'
"""))
for row in r: print(f"  {row[0]}: {row[1]}")

# Check character_attributes UNIQUE
print("\n=== character_attributes UNIQUE constraints ===")
r = conn.execute(text("""
    SELECT conname, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'character_attributes'::regclass AND contype = 'u'
"""))
for row in r: print(f"  {row[0]}: {row[1]}")

# Check indexes
print("\n=== W2 indexes ===")
for table in ['characters', 'character_states', 'character_attributes', 'story_events']:
    r = conn.execute(text(f"""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = '{table}'
    """))
    rows = list(r)
    if rows:
        print(f"  {table}:")
        for row in rows: print(f"    {row[0]}: {row[1]}")
    else:
        print(f"  {table}: (no indexes)")

# Check story_events table exists
print("\n=== story_events table ===")
r = conn.execute(text("""
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'story_events')
"""))
print(f"  Exists: {r.scalar()}")

# Check alembic_version
print("\n=== alembic_version ===")
r = conn.execute(text("SELECT version_num FROM alembic_version"))
for row in r: print(f"  {row[0]}")

conn.close()
