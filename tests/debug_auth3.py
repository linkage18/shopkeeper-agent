"""Debug auth by checking what the knowledge router sees vs auth router"""
import httpx

base = "http://localhost:8000"

# Register
r = httpx.post(f"{base}/api/auth/register", json={"username": "finaldbg", "password": "p123"})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# 1. Knowledge works
r1 = httpx.get(f"{base}/api/knowledge/list", headers=headers)
print(f"[1] Knowledge: {r1.status_code}")

# 2. Me fails
r2 = httpx.get(f"{base}/api/auth/me", headers=headers)
print(f"[2] Me: {r2.status_code} {r2.text}")

# 3. Let me try hitting me with the exact same header format
# Maybe httpx is transforming the header
print(f"[3] Headers sent: {headers}")
print(f"[4] Token length: {len(token)}")
print(f"[5] Token starts with: {token[:30]}")

# 6. Manual request
import http.client
conn = http.client.HTTPConnection("localhost", 8000)
conn.request("GET", "/api/auth/me", headers=headers)
r3 = conn.getresponse()
body = r3.read().decode()
print(f"[6] Manual Me: {r3.status} {body}")
conn.close()

# 7. Same manual request to knowledge
conn2 = http.client.HTTPConnection("localhost", 8000)
conn2.request("GET", "/api/knowledge/list", headers=headers)
r4 = conn2.getresponse()
body4 = r4.read().decode()
print(f"[7] Manual Knowledge: {r4.status} {len(body4)} bytes")
conn2.close()
