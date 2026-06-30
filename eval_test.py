import sys, json, re
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from main import app

QUESTIONS_FILE = r"D:\PythonProject\LLM\SFT\data\processed\sft_dev.jsonl"
results = {"total": 0, "correct": 0, "errors": [], "details": []}

# Load questions
questions = []
with open(QUESTIONS_FILE, encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        if d.get('db_id') == 'store_1':
            questions.append(d)

print(f'Loaded {len(questions)} questions for store_1')

with TestClient(app) as client:
    r = client.post('/api/auth/login', json={'username':'admin','password':'admin123'})
    token = r.json()['token']
    headers = {'Authorization': f'Bearer {token}'}
    
    for q in questions:
        query_text = q.get('input','').split('Question\n')[-1].split('\n')[0].strip() or q.get('question','')
        gold_sql = q.get('output','') or q.get('query','')
        
        results['total'] += 1
        
        try:
            resp = client.post('/api/query', json={'query': query_text}, headers=headers)
            gen_sql = ''
            if resp.status_code == 200:
                for line in resp.text.split('\n'):
                    line = line.strip()
                    if line.startswith('data:'):
                        try:
                            event = json.loads(line[6:])
                            if event.get('type') == 'result':
                                gen_sql = event.get('sql', '')
                        except:
                            pass
        except Exception as ex:
            gen_sql = f'ERROR: {ex}'
        
        ok = gen_sql.strip() == gold_sql.strip()
        if ok:
            results['correct'] += 1
        results['details'].append({'question': query_text[:40], 'gold': gold_sql[:50], 'generated': gen_sql[:50], 'ok': ok})
        print(f"  [{'OK' if ok else 'XX'}] {query_text[:40]}")
    
    accuracy = results['correct'] / results['total'] if results['total'] > 0 else 0
    print()
    print('store_1: ' + str(results['correct']) + '/' + str(results['total']) + ' = ' + format(accuracy, '.1%'))
    for d in results['details']:
        if not d['ok']:
            print('  XX ' + d['question'])
            print('     gold: ' + d['gold'])
            print('     gen:  ' + d['generated'])
