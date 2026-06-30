"""Check what Qdrant stores for column table_id values."""
import httpx

QDRANT_URL = "http://localhost:18933"
COLLECTION = "column_info"

# Check collection info
r = httpx.get(f"{QDRANT_URL}/collections/{COLLECTION}")
print(f"Collection '{COLLECTION}' exists: {r.status_code == 200}")
if r.status_code == 200:
    data = r.json()
    print(f"Points count: {data.get('result', {}).get('points_count', 'unknown')}")

    # Scroll a few points
    r = httpx.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll", json={
        "limit": 5,
        "with_payload": True,
        "with_vector": False
    })
    if r.status_code == 200:
        points = r.json().get("result", {}).get("points", [])
        for p in points:
            payload = p.get("payload", {})
            print(f"\n  Point id: {p['id']}")
            print(f"  table_id: {payload.get('table_id', 'N/A')}")
            print(f"  name: {payload.get('name', 'N/A')}")
            print(f"  all keys: {list(payload.keys())}")
else:
    # Try listing all collections
    r = httpx.get(f"{QDRANT_URL}/collections")
    print(f"Available collections: {r.json()}")

