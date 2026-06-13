"""测试 sqlglot AST 审查逻辑"""
import sqlglot
import py_compile

def test(sql: str, expect_block: bool):
    """expect_block=True 表示期望被阻断"""
    try:
        stmts = sqlglot.parse(sql)
        blocked = False
        for stmt in stmts:
            if stmt is None:
                continue
            if not isinstance(stmt, sqlglot.exp.Select):
                blocked = True
                break
            if stmt.find(sqlglot.exp.Into):
                blocked = True
                break
    except Exception:
        blocked = True
    
    ok = blocked == expect_block
    status = "OK" if ok else "FAIL"
    action = "阻断" if expect_block else "放行"
    actual = "阻断" if blocked else "放行"
    print(f"  [{status}] {sql[:55]:<55s} 期望={action}  实际={actual}")
    return ok


print("=== SQL 审查测试 ===\n")
ok = 0
total = 0

# 应放行（纯 SELECT）
cases = [
    ("SELECT * FROM fact_order", False),
    ("SELECT region_name, SUM(order_amount) FROM fact_order GROUP BY region_name", False),
    ("SELECT * FROM fact_order WHERE id = 1", False),
    ("SELECT COUNT(*) FROM dim_region", False),
    ("SELECT a.*, b.name FROM fact_order a JOIN dim_region b ON a.region_id = b.id", False),
]

for sql, block in cases:
    if test(sql, block): ok += 1
    total += 1

# 应阻断（非 SELECT 或危险 SELECT）
cases_block = [
    ("UPDATE fact_order SET order_amount = 0 WHERE id = 1", True),
    ("DELETE FROM fact_order WHERE id = 1", True),
    ("INSERT INTO fact_order VALUES (1, 100)", True),
    ("DROP TABLE fact_order", True),
    ("SELECT * INTO OUTFILE '/tmp/data.csv' FROM fact_order", True),
    ("TRUNCATE TABLE fact_order", True),
    ("ALTER TABLE fact_order DROP COLUMN amount", True),
    ("CREATE TABLE temp AS SELECT * FROM fact_order", True),
]

for sql, block in cases_block:
    if test(sql, block): ok += 1
    total += 1

print(f"\n通过: {ok}/{total}")

# 编译验证 run_sql.py
py_compile.compile("app/agent/nodes/run_sql.py", doraise=True)
print("run_sql.py 编译: OK")
