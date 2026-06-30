import json

data = [json.loads(l) for l in open(r'D:\PythonProject\LLM\SFT\data\processed\sft_dev.jsonl', 'r', encoding='utf-8')]
store = [d for d in data if d.get('db_id') == 'store_1']
print(f"Total store_1 questions: {len(store)}")
for i, d in enumerate(store):
    inp = d.get('input', '')
    q = inp.split('Question\n')[-1].split('\n')[0].strip() if 'Question\n' in inp else d.get('question','')
    gold = (d.get('output','') or d.get('query','')).strip()
    print(f"  Q{i+1}: {q[:60]}")
    print(f"       Gold: {gold[:80]}")
