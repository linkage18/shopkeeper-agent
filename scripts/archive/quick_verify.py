"""Quick verification: login + NL2SQL query."""
import httpx

BASE = "http://127.0.0.1:8000"

r = httpx.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
print(f"Login: {r.status_code}")
token = r.json()["token"]
print(f"Token: {token[:20]}...")

r2 = httpx.post(
    f"{BASE}/api/query",
    json={"query": "\u6309\u5b57\u6bcd\u5347\u5e8f\u6392\u5217\u7684\u6240\u6709\u4e13\u8f91\u7684\u6807\u9898\u662f\u4ec0\u4e48\uff1f"},
    headers={"Authorization": f"Bearer {token}"},
    timeout=60,
)
print(f"Query: {r2.status_code}")
has_sql = '"sql"' in r2.text[:1000]
has_rows = '"rows"' in r2.text[:1000]
print(f"Has SQL: {has_sql}, Has rows: {has_rows}")
if has_sql:
    import json
    print(f"Full response text (first 2000 chars):")
    print(r2.text[:2000])
    for line in r2.text.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                event = json.loads(line[6:])
                if event.get("type") == "result":
                    data = event.get("data", {})
                    print(f"Result SQL: {data.get('sql', '')[:80]}")
                    print(f"Row count: {len(data.get('rows', []))}")
            except:
                pass
