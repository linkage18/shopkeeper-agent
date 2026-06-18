"""Force reload reports executor and test"""
import sys; sys.path.insert(0, ".")
import importlib
import app.reports.executor as exe
importlib.reload(exe)

tmpl = exe.load_template("trend")
params = {"metric": "order_amount", "granularity": "month", "start_date": 20250101, "end_date": 20250331}
sqls = exe.render_sql(tmpl, params)
for s in sqls:
    print(f"SQL [{s['id']}]: {s['sql'][:120]}")
    has_braces = "{" in s["sql"]
    print(f"  Has unreplaced placeholders: {has_braces}")

print("Test complete")
