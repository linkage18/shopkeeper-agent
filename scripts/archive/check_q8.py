"""Check Q8: compare gold vs generated SQL results."""
import sqlite3

DB = r'D:\PythonProject\LLM\SFT\data\databases\store_1.sqlite'
conn = sqlite3.connect(DB)

gold = "SELECT T2.name FROM genres AS T1 JOIN tracks AS T2 ON T1.id = T2.genre_id JOIN media_types AS T3 ON T3.id = T2.media_type_id WHERE T1.name = '摇滚' OR T3.name = 'MPEG'"
gen = "SELECT t.name AS track_name FROM tracks t LEFT JOIN genres g ON t.genre_id = g.id LEFT JOIN media_types m ON t.media_type_id = m.id WHERE g.name = 'Rock' OR m.name = 'MPEG audio file'"

print("=== Gold SQL (uses Chinese values) ===")
print(gold)
try:
    rows = conn.execute(gold).fetchall()
    print(f"Rows: {len(rows)}")
    for r in rows[:5]:
        print(f"  {r[0]}")
except Exception as e:
    print(f"Error: {e}")

print()
print("=== Generated SQL (uses English values - correct for this DB) ===")
print(gen)
try:
    rows = conn.execute(gen).fetchall()
    print(f"Rows: {len(rows)}")
    for r in rows[:5]:
        print(f"  {r[0]}")
except Exception as e:
    print(f"Error: {e}")

# Also check what kind of results the gold would return without the WHERE clause
print()
print("=== Checking actual DB values ===")
g = conn.execute("SELECT name FROM genres").fetchall()
print(f"Genres: {[r[0] for r in g]}")
m = conn.execute("SELECT name FROM media_types").fetchall()
print(f"Media types: {[r[0] for r in m]}")

conn.close()
