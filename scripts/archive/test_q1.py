"""Test Q1 only - quick check."""
import httpx
import json

BASE = "http://127.0.0.1:8000"

r = httpx.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
token = r.json()['token']
headers = {"Authorization": f"Bearer {token}"}

r = httpx.post(f"{BASE}/api/query", json={"query": "按字母升序排列的所有专辑的标题是什么？"}, headers=headers, timeout=60)
print("Status:", r.status_code)
for line in r.text.split("\n"):
    line = line.strip()
    if line.startswith("data: "):
        try:
            event = json.loads(line[6:])
            if event.get("type") == "result":
                data = event.get("data", {})
                sql = data.get("sql", "")
                print(f"Generated SQL: {sql}")
            elif event.get("type") == "progress":
                pass
            elif event.get("type") == "error":
                print(f"Error: {event}")
        except:
            pass
