"""Verify Q8 value substitution works with DISTINCT."""
import sqlite3
import re

DB = r'D:\PythonProject\LLM\SFT\data\databases\store_1.sqlite'
conn = sqlite3.connect(DB)

gold = '''SELECT T2.name FROM genres AS T1 JOIN tracks AS T2 ON T1.id = T2.genre_id JOIN media_types AS T3 ON T3.id = T2.media_type_id WHERE T1.name = "摇滚" OR T3.name = "MPEG"'''
gen = "SELECT DISTINCT t.name AS 曲目名称 FROM tracks t JOIN genres g ON t.genre_id = g.id JOIN media_types mt ON t.media_type_id = mt.id WHERE g.name = 'Rock' OR mt.name = 'MPEG audio file'"

g = conn.execute(gold).fetchall()
gen_r = conn.execute(gen).fetchall()
print(f'Gold rows: {len(g)}')
print(f'Gen rows: {len(gen_r)}')

# Extract and substitute
def extract_values(sql):
    single = re.findall(r"'([^']*)'", sql)
    double = re.findall(r'"([^"]*)"', sql)
    return single or double

gold_vals = extract_values(gold)
gen_vals = extract_values(gen)
print(f'Gold values: {gold_vals}')
print(f'Gen values: {gen_vals}')

# Substitute gen's values into gold
sub = gold
for old, new in zip(gold_vals, gen_vals[:len(gold_vals)]):
    sub = sub.replace(f'"{old}"', f"'{new}'", 1)
    sub = sub.replace(f"'{old}'", f"'{new}'", 1)

print(f'Substituted gold: {sub}')
sub_rows = conn.execute(sub).fetchall()
print(f'Sub rows: {len(sub_rows)}')
print(f'Same sorted: {sorted(sub_rows) == sorted(gen_r)}')

conn.close()
