"""Improved sqlglot-based SQL comparison for eval."""
import sqlglot
from sqlglot import exp

def _canonical_alias_map(tree):
    """Build alias map from table order: first table -> T1, second -> T2, etc."""
    alias_map = {}
    counter = [0]
    
    def collect(node):
        if isinstance(node, exp.Table):
            alias = node.args.get("alias")
            if alias and isinstance(alias, exp.TableAlias):
                name = alias.name
                if name not in alias_map:
                    counter[0] += 1
                    alias_map[name] = f"T{counter[0]}"
        return node
    
    tree.transform(collect)
    return alias_map


def normalize_sql(sql: str) -> str:
    """Normalize SQL for comparison: canonical aliases, strip ASC/column aliases."""
    try:
        tree = sqlglot.parse_one(sql, dialect="mysql").copy()
    except Exception:
        return sql.strip().upper()

    alias_map = _canonical_alias_map(tree)

    # Replace aliases
    def replace_aliases(node):
        if isinstance(node, exp.Table):
            alias = node.args.get("alias")
            if alias and isinstance(alias, exp.TableAlias):
                orig = alias.name
                if orig in alias_map:
                    # Remove old alias, set new
                    node.set("alias", exp.TableAlias(this=exp.to_identifier(alias_map[orig])))
        if isinstance(node, exp.Column):
            table = node.args.get("table")
            if table and table.this in alias_map:
                node.set("table", exp.to_identifier(alias_map[table.this]))
        return node

    tree = tree.transform(replace_aliases)

    # Strip column aliases (AS xxx)
    def strip_col_aliases(node):
        if isinstance(node, exp.Alias):
            return node.this.copy()
        return node

    tree = tree.transform(strip_col_aliases)

    # Strip ASC in ORDER BY (default)
    def strip_asc(node):
        if isinstance(node, exp.Order):
            for expr in node.expressions:
                if isinstance(expr, exp.Ordered):
                    if expr.args.get("desc") is None:
                        expr.set("asc", None)
        return node

    tree = tree.transform(strip_asc)

    return tree.sql(dialect="mysql", pretty=False)


def sql_equivalent_ast(gold_sql: str, gen_sql: str) -> bool:
    """Compare two SQL strings using alias-normalized AST."""
    if not gold_sql or not gen_sql:
        return False
    gold_norm = normalize_sql(gold_sql)
    gen_norm = normalize_sql(gen_sql)
    return gold_norm == gen_norm


# Test with actual eval data
test_cases = [
    # Q1: Should match - just column alias + ASC difference
    ("SELECT title FROM albums ORDER BY title;",
     "SELECT title AS 专辑标题 FROM albums ORDER BY title ASC"),
    # Q2: Should match 
    ('SELECT address FROM employees WHERE first_name = "Nancy" AND last_name = "Edwards";',
     "SELECT address FROM employees WHERE first_name = 'Nancy' AND last_name = 'Edwards'"),
    # Q3: Alias + JOIN table order
    ('SELECT T2.name FROM genres AS T1 JOIN tracks AS T2 ON T1.id = T2.genre_id WHERE T1.name = "Rock";',
     "SELECT t.name AS track_name FROM tracks t JOIN genres g ON t.genre_id = g.id WHERE g.name = 'Rock'"),
    # Q4: Self-join alias + condition order
    ('SELECT T2.first_name , T2.last_name FROM employees AS T1 JOIN employees AS T2 ON T1.id = T2.reports_to WHERE T1.first_name = "袁" AND T1.last_name = "熙";',
     "SELECT e.first_name, e.last_name FROM employees e JOIN employees m ON e.reports_to = m.id WHERE m.last_name = '袁' AND m.first_name = '熙'"),
    # Q6: Should match - just ASC
    ("SELECT title FROM albums WHERE title LIKE 'A%' ORDER BY title;",
     "SELECT title FROM albums WHERE title LIKE 'A%' ORDER BY title ASC"),
    # Q7: Alias + JOIN order + ASC
    ('SELECT T1.first_name ,  T1.last_name FROM customers AS T1 JOIN invoices AS T2 ON T2.customer_id  =  T1.id ORDER BY total LIMIT 10;',
     "SELECT c.first_name, c.last_name FROM invoices i JOIN customers c ON i.customer_id = c.id ORDER BY i.total ASC LIMIT 10"),
    # Q9: Should match - just quotes
    ('SELECT country FROM customers WHERE first_name = "Roberto" AND last_name = "Almeida";',
     "SELECT country AS country FROM customers WHERE first_name = 'Roberto' AND last_name = 'Almeida'"),
]

print(f"{'Result':>8} | Compared SQL pairs")
print("=" * 80)
for gold, gen in test_cases:
    eq = sql_equivalent_ast(gold, gen)
    status = "MATCH" if eq else "DIFF"
    gold_short = gold.replace('\n', ' ')[:50]
    gen_short = gen.replace('\n', ' ')[:50]
    print(f"{status:>8} | Gold: {gold_short}")
    print(f"{'':8}  | Gen:  {gen_short}")
    if not eq:
        g_norm = normalize_sql(gold)
        gen_norm = normalize_sql(gen)
        print(f"{'':8}  | G->   {g_norm[:60]}")
        print(f"{'':8}  | Gen-> {gen_norm[:60]}")
    print()
