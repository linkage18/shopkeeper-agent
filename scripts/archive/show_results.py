"""Show detailed eval results."""
import json

with open("reports/eval_store_1.jsonl", encoding="utf-8") as f:
    for i, line in enumerate(f):
        d = json.loads(line)
        ok = "OK" if d.get("correct") else "XX"
        gen = d.get("generated", "")[:100]
        gold = d.get("gold", "")[:100]
        print(f"{ok} Q{i+1}")
        print(f"    gen:  {gen}")
        print(f"    gold: {gold}")
        print()
