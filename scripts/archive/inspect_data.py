"""Inspect the eval test data."""
import json

path = r"D:\PythonProject\LLM\SFT\data\processed\sft_dev.jsonl"

items = []
with open(path, encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        if d.get("db_id") == "store_1":
            items.append(d)

print(f"Total store_1 questions: {len(items)}")
for i, item in enumerate(items[:5]):
    print(f"\n--- Q{i+1} ---")
    inp = item.get("input", "")
    print(f"  input (first 200): {inp[:200]}")
    print(f"  question: {item.get('question', '')}")
    out = item.get("output", "")
    print(f"  output (first 150): {out[:150]}")
    print(f"  query: {item.get('query', '')[:150]}")
    print(f"  db_id: {item.get('db_id', '')}")

# Show the full question for Q1
print("\n\n=== Full input for Q1 ===")
print(items[0].get("input", ""))
print("\n=== Full output for Q1 ===")
print(items[0].get("output", ""))
