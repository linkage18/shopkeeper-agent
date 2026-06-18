import httpx

base = "http://localhost:8000"

r = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

tests = [
    ("上个月华东区GMV是多少", "sql"),
    ("年假多少天", "rag"),
    ("分析一下今年Q1的销售趋势", "analysis"),
]
for q, expected in tests:
    r = httpx.post(f"{base}/api/intent/classify", headers=headers, json={"query": q})
    intent = r.json().get("intent", "")
    ok = "OK" if intent == expected else "FAIL"
    print(f"[{ok}] {q} -> {intent} (expected {expected})")

r = httpx.get(f"{base}/api/auth/me", headers=headers)
print(f"Me: {r.status_code}")

r = httpx.post(f"{base}/api/reports/analyze", headers=headers, json={
    "template_id": "trend",
    "params": {"metric": "order_amount", "granularity": "month", "start_date": 20250101, "end_date": 20250331}
})
print(f"Trend analyze: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"  SQLs: {list(d['results'].keys())}, report: {len(d['report_md'])} chars")
