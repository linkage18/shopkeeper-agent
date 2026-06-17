import httpx

base = "http://localhost:8000"

r = httpx.post(f"{base}/api/auth/register", json={"username": "dbg2", "password": "p123"})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

print("=== Test 1: Knowledge (uses require_user) ===")
r1 = httpx.get(f"{base}/api/knowledge/list", headers=headers)
print(f"  Status: {r1.status_code}")
print(f"  Items: {len(r1.json().get('items',[]))}")

print("\n=== Test 2: Me (uses require_user) ===")
r2 = httpx.get(f"{base}/api/auth/me", headers=headers)
print(f"  Status: {r2.status_code}")
print(f"  Body: {r2.text}")

print("\n=== Test 3: Raw headers echo ===")
# Direct hit on a debug endpoint to see headers
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app_dbg = FastAPI()
@app_dbg.get("/debug-headers")
async def debug_headers(request: Request):
    return JSONResponse(dict(request.headers))

# Can't easily test this inline, skip
print("  (skipped)")

print("\n=== Test 4: Verify token locally ===")
from app.auth.jwt import verify_token
payload = verify_token(token)
print(f"  Token valid: {payload is not None}")
if payload:
    print(f"  User: {payload.get('username')}")
