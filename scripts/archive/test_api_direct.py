"""Test the API directly and see the SSE response."""
import httpx
import re

BASE = "http://localhost:8000"

# Login
r = httpx.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
if r.status_code != 200:
    print(f"Login failed: {r.text}")
    exit(1)
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Test Q1: simple query
query = "按字母升序排列的所有专辑的标题是什么？"
print(f"Query: {query}")
r = httpx.post(f"{BASE}/api/query", json={"query": query}, headers=headers, timeout=60)
print(f"Status: {r.status_code}")
print(f"Full response ({len(r.text)} chars):")
print(r.text[:2000])
print("\n---")

# Check if the regex used in eval would match
match = re.search(r'"sql":"([^"]+)"', r.text)
if match:
    print(f"\nRegex match: {match.group(1)[:100]}")
else:
    print("\nRegex did NOT match!")
    
# Try another regex for escaped quotes
match2 = re.search(r'"sql":"((?:[^"\\]|\\.)*)"', r.text)
if match2:
    print(f"Escaped regex match: {match2.group(1)[:100]}")
else:
    print("Escaped regex also did NOT match!")
