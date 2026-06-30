"""Test a single query with proper SSE parsing."""
import httpx
import json

BASE = "http://localhost:8000"

# Login
r = httpx.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

query = "按字母升序排列的所有专辑的标题是什么？"
print(f"Query: {query}")
r = httpx.post(f"{BASE}/api/query", json={"query": query}, headers=headers, timeout=120)
print(f"Status: {r.status_code}")
print(f"Response length: {len(r.text)}")

# Extract SQL using JSON parsing
sql = ""
for line in r.text.split("\n"):
    line = line.strip()
    if line.startswith("data: "):
        try:
            event = json.loads(line[6:])
            if event.get("type") == "result":
                sql = event.get("data", {}).get("sql", "")
                break
        except json.JSONDecodeError:
            continue

print(f"\nExtracted SQL: {sql}")

# Gold SQL
gold = "SELECT title FROM albums ORDER BY title;"
print(f"Gold SQL:      {gold}")
print(f"Match: {sql.strip() == gold.strip()}")
