"""Check Q10 execution comparison."""
import sqlite3

DB = r'D:\PythonProject\LLM\SFT\data\databases\store_1.sqlite'
conn = sqlite3.connect(DB)

gold = 'SELECT T1.first_name, T1.last_name FROM employees AS T1 JOIN customers AS T2 ON T1.id = T2.support_rep_id GROUP BY T1.id ORDER BY COUNT(*) DESC LIMIT 1'
gen = "SELECT CONCAT(e.first_name, ' ', e.last_name) AS full_name FROM customers c JOIN employees e ON c.support_rep_id = e.id GROUP BY e.id, e.first_name, e.last_name ORDER BY COUNT(c.id) DESC LIMIT 1"

g = conn.execute(gold).fetchall()
gen_r = conn.execute(gen).fetchall()
print('Gold:', g)
print('Gen:', gen_r)

g_flat = sorted([' '.join(str(c) for c in r) for r in g])
gen_flat = sorted([' '.join(str(c) for c in r) for r in gen_r])
print('Gold flat:', g_flat)
print('Gen flat:', gen_flat)
print('Same flattened:', g_flat == gen_flat)
conn.close()
