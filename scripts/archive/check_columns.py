"""Check the actual column names in MySQL dw database vs what the system serves."""
import requests
import json

BASE = "http://127.0.0.1:8000"

# Login
r = requests.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
token = r.json()['token']
headers = {"Authorization": f"Bearer {token}"}

# Check employees table columns
r = requests.post(f"{BASE}/api/query", json={"query": "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_NAME = 'employees' AND TABLE_SCHEMA = 'dw'"}, headers=headers, timeout=30)
print(r.text[:2000])
