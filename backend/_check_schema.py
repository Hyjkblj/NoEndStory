"""临时脚本：检查当前数据库列结构"""
from sqlalchemy import create_engine, inspect
e = create_engine('postgresql://postgres:000000@localhost:5432/noendstory')
insp = inspect(e)
print('=== all tables ===')
for t in insp.get_table_names(): print(f'  {t}')
print()
for table in ['characters', 'character_states', 'character_attributes']:
    print(f'=== {table} columns ===')
    for c in insp.get_columns(table):
        print(f'  {c["name"]}')
    print(f'=== {table} constraints ===')
    for c in insp.get_unique_constraints(table):
        print(f'  UNIQUE: {c["name"]} -> {c["column_names"]}')
    for c in insp.get_check_constraints(table):
        print(f'  CHECK: {c["name"]} -> {c["sqltext"]}')
    print(f'=== {table} indexes ===')
    for i in insp.get_indexes(table):
        print(f'  INDEX: {i["name"]} -> {i["column_names"]}')
    print()
