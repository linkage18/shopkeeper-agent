"""Live integration test - run with backend running"""
import httpx
import sys

BASE = "http://localhost:8000"

def test():
    # Register
    r = httpx.post(f"{BASE}/api/auth/register", json={"username": "livetest", "password": "p123"})
    assert r.status_code == 200, f"Register failed: {r.text}"
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[PASS] Register: got token {token[:30]}...")

    # Me
    r2 = httpx.get(f"{BASE}/api/auth/me", headers=headers)
    assert r2.status_code == 200, f"Me failed: {r2.status_code} {r2.text}"
    user = r2.json().get("user", {})
    assert user.get("username") == "livetest"
    print(f"[PASS] Me: {user['username']} / {user['role']}")

    # Knowledge list
    r3 = httpx.get(f"{BASE}/api/knowledge/list", headers=headers)
    assert r3.status_code == 200
    items = r3.json().get("items", [])
    assert len(items) >= 2, f"Expected >=2 knowledge items, got {len(items)}"
    print(f"[PASS] Knowledge: {len(items)} items")

    # Reports templates
    r4 = httpx.get(f"{BASE}/api/reports/templates", headers=headers)
    assert r4.status_code == 200
    tmpls = r4.json().get("templates", [])
    assert len(tmpls) >= 5
    print(f"[PASS] Templates: {len(tmpls)}")

    # Analyze
    r5 = httpx.post(f"{BASE}/api/reports/analyze", headers=headers, json={
        "template_id": "topn",
        "params": {
            "metric": "order_amount", "dimension": "category",
            "dim_table": "dim_product", "dim_key": "product_id",
            "dim_name_field": "category", "top_n": 5,
            "start_date": 20250101, "end_date": 20250331
        }
    })
    assert r5.status_code == 200, f"Analyze failed: {r5.status_code} {r5.text[:200]}"
    data = r5.json()
    assert len(data.get("results", {})) > 0
    print(f"[PASS] Analyze: {len(data['results'])} SQL results")
    print(f"       report: {len(data['report_md'])} chars")
    print(f"       chart: {'yes' if data.get('chart_b64') else 'no'}")

    # Unauthorized access
    r6 = httpx.get(f"{BASE}/api/knowledge/list")
    assert r6.status_code == 401, f"Should be 401, got {r6.status_code}"
    print(f"[PASS] Unauthorized blocked correctly")

    print(f"\n=== {sys.argv[0]}: ALL {5} TESTS PASSED ===")

if __name__ == "__main__":
    test()
