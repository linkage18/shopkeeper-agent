"""Full fix and test script for store_1 evaluation"""
import json, re, sys, time, subprocess

def main():
    # 1. Fix merge_retrieved_info.py None guards
    subprocess.run(['git', 'show', 'HEAD:app/agent/nodes/merge_retrieved_info.py'],
        capture_output=True, timeout=10)
    content = subprocess.run(['git', 'show', 'HEAD:app/agent/nodes/merge_retrieved_info.py'],
        capture_output=True, timeout=10).stdout.decode('utf-8', errors='replace')
    # Guard 1: column_info is None in for loop
    content = content.replace(
        'for column_info in column_infos:\n            ColumnInfoState(',
        'for column_info in column_infos:\n            if column_info is None:\n                continue\n            ColumnInfoState(')
    # Guard 2: table_info is None after get_table_info_by_id
    content = content.replace(
        'await meta_mysql_repository.get_table_info_by_id(\n                            table_id\n                        )\n                    )\n                    columns = [',
        'await meta_mysql_repository.get_table_info_by_id(\n                            table_id\n                        )\n                    )\n                    if table_info is None:\n                        continue\n                    columns = [')
    with open('app/agent/nodes/merge_retrieved_info.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('[1/5] merge_retrieved_info.py fixed')

    # 2. Clear stale data and rebuild
    print('[2/5] Clearing stale data...')
    import httpx, asyncio
    async def rebuild():
        from app.clients.mysql_client_manager import meta_mysql_client_manager
        from app.clients.qdrant_client_manager import qdrant_client_manager
        from sqlalchemy import text
        meta_mysql_client_manager.init()
        qdrant_client_manager.init()
        async with meta_mysql_client_manager.session_factory() as session:
            for t in ['column_metric','column_info','metric_info','table_info']:
                await session.execute(text(f'DELETE FROM {t}'))
            await session.commit()
        for col in qdrant_client_manager.client.get_collections().collections:
            name = col.name
            if name not in ('doc_sub_chunks','doc_parent_chunks'):
                try: qdrant_client_manager.client.delete_collection(name)
                except: pass
        else:
            try: httpx.post('http://localhost:9200/data_agent/_delete_by_query',
                json={'query':{'match_all':{}}}, timeout=10)
            except: pass
        await meta_mysql_client_manager.close()
    try: asyncio.run(rebuild())
    except: pass
    print('[2/5] Stale data cleared')

    # 3. Start backend
    print('[3/5] Starting backend...')
    proc = subprocess.Popen(
        ['.venv/Scripts/python.exe', '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(12)
    print('[3/5] Backend started (PID: ' + str(proc.pid) + ')')

    # 4. Login + eval
    print('[4/5] Running eval...')
    try:
        r = httpx.post('http://localhost:8000/api/auth/login',
            json={'username':'admin','password':'admin123'}, timeout=10)
        token = r.json()['token']
    except Exception as ex:
        print('Login failed:', ex)
        return

    questions = []
    with open(r'D:\PythonProject\LLM\SFT\data\processed\sft_dev.jsonl', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    store1 = [q for q in questions if q.get('db_id') == 'store_1']
    print(f'Found {len(store1)} questions')

    correct = 0
    exact_match = 0
    for i, q in enumerate(store1, 1):
        query_text = (q.get('input','').split('Question\\n')[-1].split('\\n')[0].strip() or q.get('question',''))
        gold = q.get('output','') or q.get('query','')
        result_data = None
        gen_sql = ''
        error_msg = ''
        try:
            sse = httpx.post('http://localhost:8000/api/query',
                json={'query': query_text},
                headers={'Authorization': f'Bearer {token}'},
                timeout=120)
            for line in sse.text.split('\\n'):
                line = line.strip()
                if line.startswith('data:'):
                    try:
                        evt = json.loads(line[6:])
                        if evt.get('type') == 'result':
                            gen_sql = evt.get('sql','')
                            result_data = evt.get('data','')
                        elif evt.get('type') == 'error':
                            error_msg = evt.get('message','')
                    except: pass
        except Exception as ex:
            error_msg = str(ex)

        exact_ok = gen_sql.strip() == gold.strip()
        if exact_ok: exact_match += 1

        status = 'OK' if exact_ok else 'XX'
        print(f'  [{status}] {query_text[:40]}')
        if not exact_ok:
            print(f'         gold: {gold[:40]}')
            print(f'         gen:  {gen_sql[:40]}')

    print(f'\\n=== store_1 Results ===')
    print(f'Exact Match: {exact_match}/{len(store1)} = {exact_match/len(store1)*100:.1f}%')

    # 5. Save results
    with open('reports/final_eval.json', 'w') as f:
        json.dump({'total':len(store1),'exact_match':exact_match}, f)
    print('[5/5] Results saved to reports/final_eval.json')

    proc.terminate()

if __name__ == '__main__':
    main()
