import json

data = [json.loads(l) for l in open('reports/eval_store_1.jsonl', 'r', encoding='utf-8')]
correct = sum(1 for d in data if d.get('correct'))
print(f'Results: {correct}/{len(data)} = {correct/len(data)*100:.1f}%')
print()
for i, d in enumerate(data):
    ok = 'OK' if d['correct'] else 'XX'
    print(f'  [{ok}] Q{i+1}: {d["query"][:50]}')
    if not d['correct']:
        gen = d['generated'][:60] if d['generated'] else '(empty)'
        print(f'        generated: {gen}')
