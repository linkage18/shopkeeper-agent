"""Check eval results in detail."""
import json

with open("reports/eval_store_1.jsonl", encoding="utf-8") as f:
    for i, line in enumerate(f):
        d = json.loads(line)
        print(f"--- Q{i+1} ---")
        print(f"  query:     {d.get('query','')[:60]}")
        print(f"  gold:      {d.get('gold','')[:120]}")
        gen = d.get('generated','')
        print(f"  generated: {gen[:150]}")
        print(f"  correct:   {d.get('correct')}")
        if gen:
            print(f"  exact_match: {repr(gen) == repr(d.get('gold',''))}")
