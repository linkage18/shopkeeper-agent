import sqlite3
import sys

conn = sqlite3.connect(r'D:\PythonProject\LLM\SFT\data\databases\store_1.sqlite')
rows = conn.execute('SELECT first_name, last_name FROM customers').fetchall()
for r in rows:
    # Write to stdout as bytes to bypass console encoding issues
    sys.stdout.buffer.write(f'{r[0]} {r[1]}\n'.encode('utf-8'))
conn.close()
