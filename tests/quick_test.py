import httpx

base = "http://localhost:8000"

r = httpx.post(f"{base}/api/auth/register", json={"username": "final99", "password": "p123"})
token = r.json()["token"]
print(f"Token: {token[:30]}...")

me = httpx.get(f"{base}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
print(f"ME status: {me.status_code}")
print(f"ME body: {me.text[:300]}")

kn = httpx.get(f"{base}/api/knowledge/list", headers={"Authorization": f"Bearer {token}"})
print(f"KN status: {kn.status_code}")
if kn.status_code == 200:
    print(f"KN items: {len(kn.json().get('items', []))}")
