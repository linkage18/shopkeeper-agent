"""Test session save and list"""
import httpx
base = "http://localhost:8003"
r = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
t = r.json()["token"]
h = {"Authorization": f"Bearer {t}"}

# Test session save
r2 = httpx.post(f"{base}/api/session/save", headers=h, json={
    "query": "test 123",
    "answer": "3 rows",
    "summary": "test query",
    "type": "sql",
})
print(f"Save: {r2.status_code}")
if r2.status_code != 200:
    print(f"  Error: {r2.text[:200]}")

# Test session list
r3 = httpx.get(f"{base}/api/rag/sessions", headers=h)
print(f"List: {r3.status_code}")
data = r3.json()
for s in data.get("sessions", []):
    print(f"  [{s.get('type','?')}] {s['id']}: {s['first_query']}")
