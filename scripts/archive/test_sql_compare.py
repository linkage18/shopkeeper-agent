"""Test sqlglot AST comparison for alias-agnostic SQL equivalence."""
import sqlglot
from sqlglot import exp

# Test cases: semantically equivalent pairs
pairs = [
    # Different aliases, same query
    (
        "SELECT T2.name FROM genres AS T1 JOIN tracks AS T2 ON T1.id = T2.genre_id WHERE T1.name = 'Rock'",
        "SELECT t.name FROM tracks t JOIN genres g ON t.genre_id = g.id WHERE g.name = 'Rock'",
    ),
    # Different alias, different alias style
    (
        "SELECT T2.first_name, T2.last_name FROM employees AS T1 JOIN employees AS T2 ON T1.id = T2.reports_to WHERE T1.first_name = 'a' AND T1.last_name = 'b'",
        "SELECT e.first_name, e.last_name FROM employees e JOIN employees m ON e.reports_to = m.id WHERE m.first_name = 'a' AND m.last_name = 'b'",
    ),
    # Self-join with swapped condition sides
    (
        "SELECT T1.first_name, T1.last_name FROM customers AS T1 JOIN invoices AS T2 ON T2.customer_id = T1.id ORDER BY total LIMIT 10",
        "SELECT c.first_name, c.last_name FROM invoices i JOIN customers c ON i.customer_id = c.id ORDER BY i.total ASC LIMIT 10",
    ),
    # Simple query
    (
        "SELECT title FROM albums ORDER BY title",
        "SELECT title AS 专辑标题 FROM albums ORDER BY title ASC",
    ),
    # Not equivalent
    (
        "SELECT count(*) FROM albums AS T1 JOIN artists AS T2 ON T1.artist_id = T2.id WHERE T2.name = 'jay'",
        "SELECT COUNT(DISTINCT album_id) AS num FROM tracks",
    ),
]

def strip_aliases(node):
    """Recursively strip table aliases from AST for comparison."""
    if isinstance(node, exp.TableAlias):
        return None
    if isinstance(node, exp.Alias):
        # Keep the underlying expression, drop the alias
        return node.this.copy()
    if isinstance(node, exp.Table):
        # Keep table name but drop alias
        copy = node.copy()
        copy.set("alias", None)
        return copy
    return node

def normalize_ast(sql: str) -> str:
    """Parse SQL, normalize aliases, and produce comparable string."""
    try:
        tree = sqlglot.parse_one(sql, dialect="mysql")
        # Transform: replace all table alias nodes
        tree = tree.transform(strip_aliases)
        # Generate normalized SQL
        return tree.sql(dialect="mysql", pretty=False)
    except Exception as e:
        return f"PARSE_ERROR: {e}"

for i, (gold, gen) in enumerate(pairs):
    g_norm = normalize_ast(gold)
    gen_norm = normalize_ast(gen)
    eq = g_norm == gen_norm
    print(f"\n--- Pair {i+1} ---")
    print(f"  Gold:     {gold[:70]}")
    print(f"  Gen:      {gen[:70]}")
    print(f"  Gold AST: {g_norm}")
    print(f"  Gen AST:  {gen_norm}")
    print(f"  Equal:    {eq}")
