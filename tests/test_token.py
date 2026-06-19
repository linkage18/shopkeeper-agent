"""Verify token recording works"""
import httpx
base = "http://localhost:8002"
r = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
h = {"Authorization": f"Bearer {r.json()['token']}"}

# Call intent classify (uses LLM)
r = httpx.post(f"{base}/api/intent/classify", json={"query": "上个月GMV"})
print(f"Intent: {r.json()}")

# Check token stats
r = httpx.get(f"{base}/api/token/summary", headers=h)
data = r.json()
print(f"Token summary: {data}")
if data["total_calls"] > 0:
    print("[PASS] Token recording works!")
else:
    print("[WARN] No tokens recorded yet")
