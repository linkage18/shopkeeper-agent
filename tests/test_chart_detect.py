"""Test chart detection"""
import sys; sys.path.insert(0, ".")
from app.agent.nodes.run_sql import _has_chart_keyword

tests = [
    ("统计各地区销售占比", True),
    ("自动饼图", True),
    ("上个月GMV", False),
    ("生成图表", True),
]
for q, expected in tests:
    result = _has_chart_keyword(q)
    status = "PASS" if result == expected else "FAIL"
    print(f"[{status}] '{q}' -> {result} (expected {expected})")
