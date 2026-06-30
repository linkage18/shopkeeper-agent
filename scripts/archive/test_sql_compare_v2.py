"""Test sqlglot AST comparison with alias normalization to canonical form."""
import sqlglot
from sqlglot import exp

def normalize_sql(sql: str) -> str:
    """Parse SQL, normalize aliases to canonical form, and produce comparable string."""
    try:
        tree = sqlglot.parse_one(sql, dialect="mysql")
        # Step 1: Collect table alias definitions in order of appearance
        alias_map = {}  # original alias -> canonical alias (T1, T2, ...)
        counter = [0]
        
        def collect_aliases(node):
            if isinstance(node, exp.Table):
                alias = node.args.get("alias")
                if alias and isinstance(alias, exp.TableAlias):
                    name = alias.name
                    if name not in alias_map:
                        counter[0] += 1
                        alias_map[name] = f"T{counter[0]}"
            return node
        
        tree = tree.copy()
        tree = tree.transform(collect_aliases)
        
        # Step 2: Replace all alias references with canonical form
        def replace_aliases(node):
            if isinstance(node, exp.Table):
                alias = node.args.get("alias")
                if alias and isinstance(alias, exp.TableAlias):
                    orig = alias.name
                    if orig in alias_map:
                        alias.pop()
                        node.set("alias", exp.TableAlias(this=alias_map[orig]))
            if isinstance(node, exp.Column):
                table = node.args.get("table")
                if table and table.this in alias_map:
                    node.set("table", exp.to_identifier(alias_map[table.this]))
            return node
        
        tree = tree.transform(replace_aliases)
        
        # Step 3: Remove column aliases (AS xxx) for comparison
        def strip_col_aliases(node):
            if isinstance(node, exp.Alias):
                return node.this.copy()
            return node
        
        tree = tree.transform(strip_col_aliases)
        
        # Step 4: Remove ASC (default sort)
        def strip_asc(node):
            if isinstance(node, exp.Order) and node.args.get("desc") is None:
                node.set("asc", None)
            return node
        
        tree = tree.transform(strip_asc)
        
        return tree.sql(dialect="mysql", pretty=False)
    except Exception as e:
        return f"PARSE_ERROR: {e}"

# Test cases
pairs = [
    ("SELECT T2.name FROM genres AS T1 JOIN tracks AS T2 ON T1.id = T2.genre_id WHERE T1.name = 'Rock'",
     "SELECT t.name FROM tracks t JOIN genres g ON t.genre_id = g.id WHERE g.name = 'Rock'"),
    ("SELECT T2.first_name, T2.last_name FROM employees AS T1 JOIN employees AS T2 ON T1.id = T2.reports_to WHERE T1.first_name = 'a' AND T1.last_name = 'b'",
     "SELECT e.first_name, e.last_name FROM employees e JOIN employees m ON e.reports_to = m.id WHERE m.first_name = 'a' AND m.last_name = 'b'"),
    ("SELECT T1.first_name, T1.last_name FROM customers AS T1 JOIN invoices AS T2 ON T2.customer_id = T1.id ORDER BY total LIMIT 10",
     "SELECT c.first_name, c.last_name FROM invoices i JOIN customers c ON i.customer_id = c.id ORDER BY i.total ASC LIMIT 10"),
    ("SELECT title FROM albums ORDER BY title",
     "SELECT title AS 专辑标题 FROM albums ORDER BY title ASC"),
    ("SELECT count(*) FROM albums AS T1 JOIN artists AS T2 ON T1.artist_id = T2.id WHERE T2.name = 'jay'",
     "SELECT COUNT(DISTINCT album_id) AS num FROM tracks"),
    # Edge: no alias at all
    ("SELECT * FROM albums WHERE title LIKE 'A%'",
     "SELECT * FROM albums WHERE title LIKE 'A%'"),
]

print(f"{'Result':>8} | SQL")
print("-" * 80)
for gold, gen in pairs:
    g_norm = normalize_sql(gold)
    gen_norm = normalize_sql(gen)
    eq = g_norm == gen_norm
    status = "OK" if eq else "DIFF"
    print(f"{status:>8} | Gold: {gold[:65]}")
    print(f"{'':8}  | Gen:  {gen[:65]}")
    if not eq:
        print(f"{'':8}  | Gold-> {g_norm[:65]}")
        print(f"{'':8}  | Gen->  {gen_norm[:65]}")
    print()
