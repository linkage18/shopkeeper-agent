"""Check store_1.sqlite data for eval validation."""
import sqlite3

conn = sqlite3.connect(r'D:\PythonProject\LLM\SFT\data\databases\store_1.sqlite')

# Check genres
g = conn.execute('SELECT name FROM genres').fetchall()
print('Genres:', [r[0] for r in g])

# Check media_types
m = conn.execute('SELECT name FROM media_types').fetchall()
print('Media types:', [r[0] for r in m])

# Check artists
a = conn.execute('SELECT name FROM artists LIMIT 5').fetchall()
print('Artists:', [r[0] for r in a])

# Check employees
e = conn.execute('SELECT first_name, last_name FROM employees').fetchall()
print('Employees:', [(r[0], r[1]) for r in e])

# Check customers
c = conn.execute('SELECT first_name, last_name FROM customers LIMIT 5').fetchall()
print('Customers:', [(r[0], r[1]) for r in c])

# Check what genre values gold Q8 expects vs what exists
q8_gold = conn.execute("SELECT name FROM genres WHERE name = '摇滚'").fetchall()
print("Q8 genre '摇滚':", q8_gold)

q8_gen = conn.execute("SELECT name FROM genres WHERE name = 'Rock'").fetchall()
print("Q8 genre 'Rock':", q8_gen)

q8_media_gold = conn.execute("SELECT name FROM media_types WHERE name = 'MPEG'").fetchall()
print("Q8 media 'MPEG':", q8_media_gold)

q8_media_gen = conn.execute("SELECT name FROM media_types WHERE name = 'MPEG audio file'").fetchall()
print("Q8 media 'MPEG audio file':", q8_media_gen)

conn.close()
