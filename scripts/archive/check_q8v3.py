"""Test Q8 evaluation manually."""
import sqlite3
import re

DB = r'D:\PythonProject\LLM\SFT\data\databases\store_1.sqlite'
conn = sqlite3.connect(DB)

gold = 'SELECT T2.name FROM genres AS T1 JOIN tracks AS T2 ON T1.id = T2.genre_id JOIN media_types AS T3 ON T3.id = T2.media_type_id WHERE T1.name = "摇滚" OR T3.name = "MPEG"'
gen = "SELECT DISTINCT t.name AS 曲目名称 FROM tracks t JOIN genres g ON t.genre_id = g.id JOIN media_types mt ON t.media_type_id = mt.id WHERE g.name = 'Rock' OR mt.name = 'MPEG audio file'"

# Gold returns 0
g_rows = conn.execute(gold).fetchall()
gen_rows = conn.execute(gen).fetchall()
print(f'Gold: {len(g_rows)} rows')
print(f'Gen: {len(gen_rows)} rows')

# Value substitution
gold_vals = re.findall(r'"([^"]*)"', gold)  # ['摇滚', 'MPEG']
gen_vals = re.findall(r"'([^']*)'", gen)  # ['Rock', 'MPEG audio file']

sub = gold
for old, new in zip(gold_vals, gen_vals[:len(gold_vals)]):
    sub = sub.replace(f'"{old}"', f"'{new}'", 1)

print(f'Substituted: {sub[:100]}')
sub_rows = conn.execute(sub).fetchall()
print(f'Sub rows: {len(sub_rows)}')
print(f'Same sorted(rows): {sorted(sub_rows) == sorted(gen_rows)}')
print(f'Set gold == set gen: {set(sub_rows) == set(gen_rows)}')
print(f'Sorted set gold == sorted set gen: {sorted(set(sub_rows)) == sorted(set(gen_rows))}')

conn.close()
