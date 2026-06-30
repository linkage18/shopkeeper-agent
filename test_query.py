import sys, json
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from main import app

with TestClient(app) as client:
    r = client.post('/api/auth/login', json={'username':'admin','password':'admin123'})
    h = {'Authorization': f'Bearer {r.json()["token"]}'}
    
    q = "select title from albums order by title limit 1"
    resp = client.post('/api/query', json={'query': q}, headers=h, timeout=120)
    print('Status:', resp.status_code)
    lines = resp.text.split('\n')
    data_lines = [l for l in lines if l.strip().startswith('data:')]
    print('data: lines:', len(data_lines))
    for dl in data_lines[-3:]:
        print(dl[:150])
        try:
            evt = json.loads(dl[6:])
            print('  type:', evt.get('type'))
            if evt.get('type') == 'result':
                print('  sql:', evt.get('sql','')[:100])
                print('  data:', str(evt.get('data',''))[:100])
        except Exception as e:
            print('  parse error:', e)
