"""Test sqlglot AST comparison for SQL equivalence."""
import sqlglot

pairs = [
    # (generated, gold, description)
    (
        "SELECT t.name FROM tracks t JOIN genres g ON t.genre_id = g.id WHERE g.name = 'Rock'",
        "SELECT T2.name FROM genres AS T1 JOIN tracks AS T2 ON T1.id = T2.genre_id WHERE T1.name = 'Rock'",
        "Q3: Rock tracks"
    ),
    (
        "SELECT c.first_name, c.last_name FROM invoices i JOIN customers c ON i.customer_id = c.id ORDER BY i.total ASC LIMIT 10",
        "SELECT T1.first_name, T1.last_name FROM customers AS T1 JOIN invoices AS T2 ON T2.customer_id = T1.id ORDER BY total ASC LIMIT 10",
        "Q7: Least expensive invoices"
    ),
    (
        "SELECT title AS 标题 FROM albums ORDER BY title ASC",
        "SELECT title FROM albums ORDER BY title",
        "Q1: Album titles sorted"
    ),
]

for gen_sql, gold_sql, desc in pairs:
    try:
        gen_tree = sqlglot.parse_one(gen_sql)
        gold_tree = sqlglot.parse_one(gold_sql)
        eq = gen_tree == gold_tree
        print(f"{'OK' if eq else 'XX'} {desc}: AST equal = {eq}")
        if not eq:
            # Show the differences
            print(f"  gen:  {gen_tree}")
            print(f"  gold: {gold_tree}")
    except Exception as e:
        print(f"ERR {desc}: {e}")
