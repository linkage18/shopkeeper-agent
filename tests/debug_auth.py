import httpx

base = "http://localhost:8000"
r = httpx.post(f"{base}/api/auth/register", json={"username": "pyu2", "password": "p123"})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

r2 = httpx.get(f"{base}/api/knowledge/list", headers=headers)
print(f"Knowledge: {r2.status_code} items={len(r2.json().get('items',[]))}")

r3 = httpx.get(f"{base}/api/auth/me", headers=headers)
print(f"Me: {r3.status_code} body={r3.text[:200]}")

# Also test require_user works for both
r4 = httpx.get(f"{base}/api/reports/templates", headers=headers)
print(f"Templates: {r4.status_code}")
