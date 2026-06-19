"""Debug: test token + schema on clean server"""
import httpx
base = "http://localhost:8000"
r = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
h = {"Authorization": f"Bearer {r.json()['token']}"}

r2 = httpx.get(f"{base}/api/schema", headers=h)
print(f"Schema: {r2.status_code}")
if r2.status_code == 200:
    d = r2.json()
    print(f"  dims={len(d.get('dimensions',[]))} meas={len(d.get('measures',[]))}")

r3 = httpx.get(f"{base}/api/token/summary", headers=h)
print(f"Token summary: {r3.json()}")

# Test intent classify for report
r4 = httpx.post(f"{base}/api/intent/classify", json={"query": "总结Q1销售情况"})
print(f"Intent report: {r4.json()}")

r5 = httpx.post(f"{base}/api/intent/classify", json={"query": "上个月GMV"})
print(f"Intent sql: {r5.json()}")
