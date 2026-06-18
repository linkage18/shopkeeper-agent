"""Debug: test compare analysis API"""
import httpx

base = "http://localhost:8000"
r = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
h = {"Authorization": f"Bearer {r.json()['token']}"}

# Test compare
r = httpx.post(f"{base}/api/reports/analyze", headers=h, json={
    "template_id": "compare",
    "params": {
        "metric": "order_amount", "dimension": "region_name",
        "dim_table": "dim_region", "dim_key": "region_id",
        "dim_name_field": "region_name",
        "start_date": 20250101, "end_date": 20250331
    }
})
d = r.json()
print(f"Status: {r.status_code}")
for k, v in d.get("results", {}).items():
    if k.endswith("_error"):
        print(f"  ERROR {k}: {v[:200]}")
    else:
        print(f"  {k}: {len(v)} rows")
print(f"Chart data: {d.get('chart_data') is not None}")
