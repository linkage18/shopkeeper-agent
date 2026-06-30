"""Compare SQL using sqlglot AST - handles aliases, ASC, semicolons."""
import sqlglot
from sqlglot import exp

def _find_aliases(tree):
    """Map original table aliases to canonical T1, T2, ... based on first appearance."""
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


def _normalize_one(sql: str) -> str:
    """Normalize a single SQL: aliases, strip ASC/col aliases, uppercase keywords."""
    s = sql.strip().rstrip(";").strip()
    if not s:
        return ""
    
    try:
        tree = sqlglot.parse_one(s, dialect="mysql").copy()
    except Exception:
        return s.upper()
    
    alias_map = _find_aliases(tree)
    
    # Replace table aliases with canonical names
    def replace_aliases(node):
        if isinstance(node, exp.Table):
            alias = node.args.get("alias")
            if alias and isinstance(alias, exp.TableAlias):
                if alias.name in alias_map:
                    node.set("alias", exp.TableAlias(this=exp.to_identifier(alias_map[alias.name])))
        if isinstance(node, exp.Column):
            table = node.args.get("table")
            if table and table.this in alias_map:
                node.set("table", exp.to_identifier(alias_map[table.this]))
        return node
    
    tree = tree.transform(replace_aliases)
    
    # Strip column aliases (SELECT expr AS name -> SELECT expr)
    def strip_aliases(node):
        if isinstance(node, exp.Alias):
            return node.this.copy()
        return node
    
    tree = tree.transform(strip_aliases)
    
    # Remove explicit ASC in ORDER BY (it's the default)
    # sqlglot: Ordered(desc=False) means ASC was explicit; Ordered(desc=None) is default
    def remove_explicit_asc(node):
        if isinstance(node, exp.Ordered):
            desc = node.args.get("desc")
            if desc is False:  # Explicit ASC, remove it
                node.args.pop("desc", None)
        return node
    
    tree = tree.transform(remove_explicit_asc)
    
    # Uppercase keywords via dialect output
    result = tree.sql(dialect="mysql", pretty=False)
    return result


def compare_sql(gold: str, generated: str) -> bool:
    """Compare gold SQL with generated SQL using alias-normalized AST."""
    if not gold or not generated:
        return False
    g = _normalize_one(gold)
    gen = _normalize_one(generated)
    if not g or not gen:
        return False
    return g == gen


# Quick test
tests = [
    # Should match: column alias + ASC difference
    (True, "SELECT title FROM albums ORDER BY title",
     "SELECT title AS t FROM albums ORDER BY title ASC"),
    # Should match: quote difference
    (True, 'SELECT address FROM employees WHERE first_name = "Nancy"',
     "SELECT address FROM employees WHERE first_name = 'Nancy'"),
    # Should NOT match: different tables
    (False, "SELECT * FROM albums", "SELECT * FROM tracks"),
    # Should match: alias only difference
    (True, "SELECT T1.name FROM artists AS T1 WHERE T1.id = 1",
     "SELECT a.name FROM artists a WHERE a.id = 1"),
]

for expected, g, gen in tests:
    result = compare_sql(g, gen)
    status = "MATCH" if result == expected else "WRONG"
    print(f"[{status}] expected={expected}, got={result} | {g[:40]}")

# Now test with actual eval data
print("\n--- Actual eval data ---")
import json
results = [json.loads(l) for l in open('reports/eval_store_1.jsonl', 'r', encoding='utf-8')]
correct_new = 0
for r in results:
    eq = compare_sql(r['gold'], r['generated'])
    if eq:
        correct_new += 1
    r['correct'] = eq
    status = "OK" if eq else "XX"
    print(f"  [{status}] {r['query'][:40]}")

print(f"\nTotal: {correct_new}/{len(results)} = {correct_new/len(results)*100:.1f}%")

# Save corrected results
with open('reports/eval_store_1_corrected.jsonl', 'w', encoding='utf-8') as f:
    for r in results:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print("Saved corrected results to reports/eval_store_1_corrected.jsonl")
