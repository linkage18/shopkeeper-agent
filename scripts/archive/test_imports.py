"""Test imports."""
import sys
sys.path.insert(0, '.')
from app.agent.nodes.run_sql import _has_chart_keyword
from app.agent.nodes.generate_sql import generate_sql
print("All imports OK")
print(f"_has_chart_keyword('test'): {_has_chart_keyword('test')}")
