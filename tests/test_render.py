"""Test render_sql directly"""
import sys; sys.path.insert(0, ".")
from app.reports.executor import load_template, render_sql

tmpl = load_template("trend")
params = {"metric": "order_amount", "granularity": "month", "start_date": 20250101, "end_date": 20250331}
sqls = render_sql(tmpl, params)
for s in sqls:
    print(s["sql"][:150])
    print()

# Check no unreplaced placeholders
for s in sqls:
    for k in params:
        assert str(params[k]) in s["sql"], f"Param {k}={params[k]} not in SQL"
    assert "{" not in s["sql"], f"Unreplaced placeholder in: {s['sql']}"

print("ALL OK")
