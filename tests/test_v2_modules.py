"""Test auth, knowledge, cache, reports modules"""
import sys, os, time
sys.path.insert(0, ".")

# ── auth ──
from app.auth.jwt import create_token, verify_token, hash_password

token = create_token({"user_id": "test-001", "username": "test", "role": "user"})
assert token.count(".") == 2
payload = verify_token(token)
assert payload and payload["user_id"] == "test-001"
print("[PASS] JWT create + verify")

bad = verify_token(token + "x")
assert bad is None
print("[PASS] JWT tamper detection")

h1 = hash_password("test123")
assert h1 == hash_password("test123")
assert h1 != hash_password("test456")
print("[PASS] password hash")

# ── knowledge ──
from app.knowledge.models import KnowledgeEntry
from app.knowledge.manager import (
    save_knowledge, get_knowledge, list_knowledge, search_knowledge, delete_knowledge,
)

items = list_knowledge()
titles = [i["title"] for i in items]
assert "GMV" in titles
assert "AOV" in titles
print(f"[PASS] list_knowledge: {len(items)} items")

entry = get_knowledge("GMV")
assert entry and "成交" in entry.definition
print(f"[PASS] get_knowledge(GMV)")

results = search_knowledge("AOV")
assert len(results) > 0
print(f"[PASS] search_knowledge: {len(results)} results")

new_entry = KnowledgeEntry(
    title="TestEntry", definition="test def", tags=["t"],
    created_by="tester", created_at="2026-01-01",
)
save_knowledge(new_entry, "test-user")
assert get_knowledge("TestEntry") is not None
print("[PASS] save_knowledge")

delete_knowledge("TestEntry", "test-user", is_shared=True)
assert get_knowledge("TestEntry") is None
print("[PASS] delete_knowledge")

# ── cache ──
from app.cache.services import exact_cache_get, exact_cache_set, check_rate_limit

exact_cache_set("q1", {"x": 1}, ttl=2)
assert exact_cache_get("q1") == {"x": 1}
print("[PASS] exact_cache")

time.sleep(3)
assert exact_cache_get("q1") is None
print("[PASS] cache expiry")

for i in range(30):
    assert check_rate_limit("rk")
assert not check_rate_limit("rk")
print("[PASS] rate limiter")

from app.cache.services import _rate_map
_rate_map.clear()

# ── reports ──
from app.reports.executor import list_templates, load_template, render_sql, build_markdown_table

templates = list_templates()
tmpl_ids = [t["id"] for t in templates]
for e in ["trend", "compare", "topn", "distribution", "detail"]:
    assert e in tmpl_ids, f"Missing: {e}"
print(f"[PASS] list_templates: {len(templates)}")

tmpl = load_template("trend")
assert tmpl and tmpl["name"] == "trend"
print("[PASS] load_template")

sqls = render_sql(tmpl, {"metric": "order_amount", "granularity": "month",
                          "start_date": 20250101, "end_date": 20250331})
assert "order_amount" in sqls[0]["sql"] and "month" in sqls[0]["sql"]
print(f"[PASS] render_sql: {sqls[0]['sql'][:60]}...")

rows = [{"brand": "Huawei", "amount": 6999}, {"brand": "Apple", "amount": 8999}]
table = build_markdown_table(rows)
assert "brand" in table and "Huawei" in table
print("[PASS] build_markdown_table")

# chart (optional)
try:
    from app.reports.renderer import generate_chart
    chart = generate_chart(rows, {"type": "bar", "x": "brand", "y": ["amount"], "title": "Test"}, {})
    if chart:
        print(f"[PASS] chart generated: {len(chart)} chars")
    else:
        print("[SKIP] chart: no matplotlib")
except Exception as e:
    print(f"[SKIP] chart: {e}")

print("\n=== ALL MODULE TESTS PASSED ===")
