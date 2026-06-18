"""Quick V3 verification on port 8001"""
import httpx
base = "http://localhost:8001"
r = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
t = r.json()["token"]
h = {"Authorization": f"Bearer {t}"}

r1 = httpx.get(f"{base}/api/schema", headers=h)
d = r1.json()
print(f"Schema: dims={len(d.get('dimensions',[]))} meas={len(d.get('measures',[]))}")

r2 = httpx.get(f"{base}/api/token/usage", headers=h)
print(f"Token: {r2.json()}")

r3 = httpx.post(f"{base}/api/intent/classify", json={"query": "总结Q1销售情况"})
print(f"Intent: {r3.json()}")

r4 = httpx.post(f"{base}/api/intent/classify", json={"query": "上个月GMV"})
print(f"Intent sql: {r4.json()}")
