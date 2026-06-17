"""FastAPI integration tests for V2 modules (no external services needed)"""
import sys
sys.path.insert(0, ".")

from fastapi.testclient import TestClient

# 启动 app（跳过 lifespan，外部服务不可用）
from main import app

client = TestClient(app)

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}: {detail}")


# ── 1. Auth endpoints ──
# Register
resp = client.post("/api/auth/register", json={"username": "testuser", "password": "test123"})
check("POST /api/auth/register 200", resp.status_code == 200)
data = resp.json()
check("  token returned", "token" in data)
check("  user data returned", "user" in data and data["user"]["username"] == "testuser")
token = data["token"]

# Duplicate register
resp2 = client.post("/api/auth/register", json={"username": "testuser", "password": "test123"})
check("POST /api/auth/register duplicate 400", resp2.status_code == 400)

# Login
resp3 = client.post("/api/auth/login", json={"username": "testuser", "password": "test123"})
check("POST /api/auth/login 200", resp3.status_code == 200)
token2 = resp3.json()["token"]
check("  login returns token", bool(token2))

# Login wrong password
resp4 = client.post("/api/auth/login", json={"username": "testuser", "password": "wrong"})
check("POST /api/auth/login wrong 401", resp4.status_code == 401)

# Get me (authenticated)
resp5 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token2}"})
check("GET /api/auth/me with token 200", resp5.status_code == 200)
check("  correct user", resp5.json()["user"]["username"] == "testuser")

# Get me (no auth)
resp6 = client.get("/api/auth/me")
check("GET /api/auth/me no auth 401", resp6.status_code == 401)

# ── 2. Knowledge endpoints ──
auth_header = {"Authorization": f"Bearer {token2}"}

resp = client.get("/api/knowledge/list", headers=auth_header)
check("GET /api/knowledge/list 200", resp.status_code == 200)
items = resp.json().get("items", [])
check("  has items", len(items) > 0)
check("  GMV exists", any(i["title"] == "GMV" for i in items))

resp = client.get("/api/knowledge/get/GMV", headers=auth_header)
check("GET /api/knowledge/get/GMV 200", resp.status_code == 200)
entry = resp.json().get("entry", {})
check("  definition found", "成交总额" in entry.get("definition", ""))

resp = client.get("/api/knowledge/search?q=AOV", headers=auth_header)
check("GET /api/knowledge/search 200", resp.status_code == 200)
check("  found AOV", any(i["title"] == "AOV" for i in resp.json().get("items", [])))

# Save new knowledge
resp = client.post("/api/knowledge/save", headers=auth_header, json={
    "title": "APITestEntry",
    "definition": "API test definition",
    "tables": ["fact_order"],
    "tags": ["test"],
    "scope": "shared",
})
check("POST /api/knowledge/save 200", resp.status_code == 200)

# Verify saved
resp = client.get("/api/knowledge/get/APITestEntry", headers=auth_header)
check("  saved entry exists", resp.status_code == 200)

# Delete
resp = client.delete("/api/knowledge/delete/APITestEntry", headers=auth_header, json={"scope": "shared"})
# 当前用户不是 admin，应该返回 403
check("DELETE non-admin shared 403", resp.status_code == 403)

# ── 3. Reports endpoints ──
resp = client.get("/api/reports/templates", headers=auth_header)
check("GET /api/reports/templates 200", resp.status_code == 200)
templates = resp.json().get("templates", [])
check("  5 templates returned", len(templates) == 5)

resp = client.get("/api/reports/templates/trend", headers=auth_header)
check("GET /api/reports/templates/trend 200", resp.status_code == 200)
check("  trend loaded", resp.json()["template"]["name"] == "trend")

# ── Summary ──
print(f"\n=== {passed} passed, {failed} failed ===")
if failed > 0:
    sys.exit(1)
