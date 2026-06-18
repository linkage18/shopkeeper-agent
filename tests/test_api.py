"""Test analyze API via HTTP"""
import httpx
base = "http://localhost:8000"

r = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
h = {"Authorization": f"Bearer {r.json()['token']}"}

r = httpx.post(f"{base}/api/reports/analyze", headers=h, json={
    "template_id": "trend",
    "params": {"metric": "order_amount", "granularity": "month", "start_date": 20250101, "end_date": 20250331}
})
d = r.json()
print(f"Status: {r.status_code}")
print(f"SQL results keys: {list(d['results'].keys())}")
has_err = any(k.endswith("_error") for k in d["results"])
print(f"Has errors: {has_err}")
print(f"Report length: {len(d['report_md'])} chars")
print(f"Chart data present: {d.get('chart_data') is not None}")
if has_err:
    for k, v in d["results"].items():
        if k.endswith("_error"):
            print(f"  ERROR {k}: {v[:150]}")
