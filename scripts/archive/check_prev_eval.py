"""Check previous eval results."""
import json

try:
    with open("reports/eval_store_1.jsonl", encoding="utf-8") as f:
        for i, line in enumerate(f):
            d = json.loads(line)
            print(f"--- Q{i+1} ---")
            print(f"  query:    {d.get('query','')[:60]}")
            print(f"  gold:     {d.get('gold','')[:100]}")
            print(f"  generated:{d.get('generated','')[:100]}")
            print(f"  correct:  {d.get('correct')}")
except FileNotFoundError:
    print("No previous eval results found.")
