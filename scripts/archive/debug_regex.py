"""Debug regex extraction from SSE response."""
import httpx
import re
import json

BASE = "http://localhost:8000"

# Login
r = httpx.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

query = "按字母升序排列的所有专辑的标题是什么？"
r = httpx.post(f"{BASE}/api/query", json={"query": query}, headers=headers, timeout=60)

text = r.text
print(f"Response length: {len(text)}")
print(f"Contains 'sql': {'sql' in text}")
print(f"Contains 'result': {'result' in text}")

# Try the exact eval regex
match = re.search(r'"sql":"([^"]+)"', text)
print(f"\nEval regex match: {match}")
if match:
    print(f"  Captured: {match.group(1)[:100]}")

# Try finding all json objects
for line in text.split('\n\n'):
    line = line.strip()
    if line.startswith('data: '):
        payload = line[6:]
        try:
            obj = json.loads(payload)
            if obj.get('type') == 'result':
                data = obj.get('data', {})
                sql = data.get('sql', '')
                print(f"\nParsed SQL from JSON: {sql[:100]}")
                print(f"Full result keys: {list(data.keys())}")
        except json.JSONDecodeError as e:
            pass

# Write raw response to file for inspection
with open('scripts/last_response.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print(f"\nFull response saved to scripts/last_response.txt")
