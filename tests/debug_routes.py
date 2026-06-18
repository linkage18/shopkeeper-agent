"""Debug: check if app can import all modules"""
import sys; sys.path.insert(0, ".")
from main import app
routes = [r.path for r in app.routes]
for r in sorted(routes):
    if "schema" in r or "viz" in r or "token" in r:
        print(f"FOUND: {r}")
print("Done")
