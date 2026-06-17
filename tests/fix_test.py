import httpx

base = "http://localhost:8000"

# Login
r = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
assert r.status_code == 200, f"Login failed: {r.text}"
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Me
r = httpx.get(f"{base}/api/auth/me", headers=headers)
print(f"Me: {r.status_code}")
if r.status_code == 200:
    print(f"  user: {r.json()['user']['username']}")

# Knowledge
r = httpx.get(f"{base}/api/knowledge/list", headers=headers)
print(f"Knowledge: {r.status_code} items={len(r.json().get('items',[]))}")

# Trend analysis
r = httpx.post(f"{base}/api/reports/analyze", headers=headers, json={
    "template_id": "trend",
    "params": {"metric": "order_amount", "granularity": "month", "start_date": 20250101, "end_date": 20250331}
})
print(f"Trend: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"  SQLs: {list(d['results'].keys())}")
    print(f"  report: {len(d['report_md'])} chars")
    print(f"  chart: {'yes' if d.get('chart_b64') else 'no'}")
else:
    print(f"  error: {r.text[:200]}")

# TopN analysis
r = httpx.post(f"{base}/api/reports/analyze", headers=headers, json={
    "template_id": "topn",
    "params": {
        "metric": "order_amount", "dimension": "category",
        "dim_table": "dim_product", "dim_key": "product_id",
        "dim_name_field": "category", "top_n": 5,
        "start_date": 20250101, "end_date": 20250331
    }
})
print(f"TopN: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"  SQLs: {list(d['results'].keys())}")
    print(f"  report: {len(d['report_md'])} chars")
    print(f"  chart: {'yes' if d.get('chart_b64') else 'no'}")
else:
    print(f"  error: {r.text[:200]}")

# Distribution analysis
r = httpx.post(f"{base}/api/reports/analyze", headers=headers, json={
    "template_id": "distribution",
    "params": {
        "metric": "order_amount", "dimension": "region_name",
        "dim_table": "dim_region", "dim_key": "region_id",
        "dim_name_field": "region_name",
        "start_date": 20250101, "end_date": 20250331
    }
})
print(f"Distribution: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"  SQLs: {list(d['results'].keys())}")
    print(f"  report: {len(d['report_md'])} chars")
else:
    print(f"  error: {r.text[:200]}")

print("\n=== DONE ===")
