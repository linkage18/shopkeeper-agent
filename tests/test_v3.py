"""Test V3 new APIs"""
import httpx
base = "http://localhost:8000"

t = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
h = {"Authorization": f"Bearer {t.json()['token']}"}

# 1. Schema
r = httpx.get(f"{base}/api/schema", headers=h)
print(f"Schema: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"  Dimensions: {len(d.get('dimensions', []))}")
    print(f"  Measures: {len(d.get('measures', []))}")
    print(f"  Tables: {len(d.get('tables', []))}")

# 2. Viz generate
r = httpx.post(f"{base}/api/viz/generate", headers=h, json={
    "dimensions": ["region_name"], "measures": ["order_amount"], "chart_type": "bar"
})
print(f"Viz: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"  Chart data: {d.get('chart_data') is not None}")
    print(f"  Table rows: {len(d.get('table_data', []))}")

# 3. Intent classify
for q in ["上个月GMV", "年假多少天", "总结Q1销售情况"]:
    r = httpx.post(f"{base}/api/intent/classify", json={"query": q})
    print(f"  Intent '{q[:12]}...' -> {r.json().get('intent')}")

# 4. Token
r = httpx.get(f"{base}/api/token/usage", headers=h)
print(f"Token usage: {r.status_code}")
print(f"  {r.json()}")

print("\nDONE")
