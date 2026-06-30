"""Deep-dive into remaining failures after meta rebuild."""
import json
import sqlite3

DB_PATH = r"D:\PythonProject\LLM\SFT\data\databases\store_1.sqlite"

results = [json.loads(l) for l in open('reports/eval_store_1.jsonl', 'r', encoding='utf-8')]

print("=== Remaining Failures Analysis ===\n")
for r in results:
    if r['correct']:
        continue
    
    print(f"[FAIL] {r['query'][:50]}")
    print(f"       Gold: {r['gold'][:80]}")
    gen = r['generated']
    if gen:
        print(f"       Gen:  {gen[:80]}")
        # Try executing gen against SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            gen_result = conn.execute(gen).fetchall()
            gold_result = conn.execute(r['gold']).fetchall()
            from pprint import pformat
            print(f"       Gold results: {pformat(gold_result)[:80]}")
            print(f"       Gen results:  {pformat(gen_result)[:80]}")
            conn.close()
        except Exception as e:
            print(f"       Exec error: {e}")
    else:
        print(f"       Gen:  (empty - LLM failed to generate)")
    print()

print("=== Q5 detailed check ===")
q5_gold = "SELECT title, phone, hire_date FROM employees WHERE first_name = '袁' AND last_name = '熙'"
print(f"Attempting: {q5_gold}")
try:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(q5_gold).fetchall()
    print(f"Result: {rows}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")

print("\n=== Q10 detailed check ===")
q10_gold = "SELECT e.first_name, e.last_name FROM employees e JOIN customers c ON e.id = c.support_rep_id GROUP BY e.id ORDER BY COUNT(*) DESC LIMIT 1"
print(f"Attempting: {q10_gold}")
try:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(q10_gold).fetchall()
    print(f"Result: {rows}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
