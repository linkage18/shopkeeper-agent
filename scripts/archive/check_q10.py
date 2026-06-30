import sqlite3

DB = r'D:\PythonProject\LLM\SFT\data\databases\store_1.sqlite'
conn = sqlite3.connect(DB)

gold = "SELECT T1.first_name, T1.last_name FROM employees AS T1 JOIN customers AS T2 ON T1.id = T2.support_rep_id GROUP BY T1.id ORDER BY COUNT(*) DESC LIMIT 1"
gen = "SELECT CONCAT(e.first_name, ' ', e.last_name) AS full_name FROM employees e JOIN (SELECT support_rep_id, COUNT(*) AS cnt FROM customers WHERE support_rep_id IS NOT NULL GROUP BY support_rep_id) c ON e.id = c.support_rep_id JOIN (SELECT MAX(cnt) AS max_cnt FROM (SELECT COUNT(*) AS cnt FROM customers WHERE support_rep_id IS NOT NULL GROUP BY support_rep_id) t) m ON c.cnt = m.max_cnt"

print("Gold SQL:", gold)
print()
try:
    gold_rows = conn.execute(gold).fetchall()
    print(f'Gold results: {gold_rows}')
except Exception as e:
    print(f'Gold error: {e}')

print()
print("Gen SQL:", gen[:100])
print()
try:
    gen_rows = conn.execute(gen).fetchall()
    print(f'Gen results: {gen_rows}')
except Exception as e:
    print(f'Gen error: {e}')

print()
print(f'Same results: {sorted(gold_rows) == sorted(gen_rows)}')
conn.close()
