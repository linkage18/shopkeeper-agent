"""Final verification on 8002"""
import httpx
base = "http://localhost:8002"
r = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
h = {"Authorization": f"Bearer {r.json()['token']}"}

r2 = httpx.get(f"{base}/api/schema", headers=h)
d = r2.json()
print(f"Schema: dims={len(d.get('dimensions',[]))} meas={len(d.get('measures',[]))}")

r3 = httpx.get(f"{base}/api/token/summary", headers=h)
print(f"Token: {r3.json()}")

r4 = httpx.post(f"{base}/api/intent/classify", json={"query": "总结Q1销售情况"})
print(f"Intent report: {r4.json()}")

r5 = httpx.post(f"{base}/api/intent/classify", json={"query": "上个月GMV"})
print(f"Intent sql: {r5.json()}")

r6 = httpx.post(f"{base}/api/intent/classify", json={"query": "年假多少天"})
print(f"Intent rag: {r6.json()}")
