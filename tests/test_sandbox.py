"""Test sandbox builtins"""
import sys; sys.path.insert(0, ".")
from app.report_agent.sandbox import run_pandas
import pandas as pd

data = {"df": pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})}

# Test with basic builtins (dict, str, int, etc.)
code1 = 'result = df.groupby("x")["y"].sum().reset_index()'
out1 = run_pandas(code1, data)
assert len(out1["result"]) == 3, f"Expected 3 rows, got {out1}"
print(f"[PASS] groupby + reset_index: {len(out1['result'])} rows")

# Test with dict()
code2 = 'result = {"a": 1, "b": 2}'
out2 = run_pandas(code2, data)
assert out2["result"] == {"a": 1, "b": 2}
print(f"[PASS] dict() works: {out2['result']}")

# Test with list()
code3 = 'result = list(range(3))'
out3 = run_pandas(code3, data)
assert out3["result"] == [0, 1, 2]
print(f"[PASS] list() works: {out3['result']}")

# Test security still works
try:
    run_pandas("import os; os.system('dir')", data)
    print("[FAIL] Should have blocked os!")
except Exception as e:
    print(f"[PASS] os blocked: {e}")

print("\nALL PASS")
