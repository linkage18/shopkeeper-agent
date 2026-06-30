"""Full evaluation: AST comparison + SQLite execution validation."""
import json, sqlite3
import sqlglot
from sqlglot import exp

DB_PATH = r"D:\PythonProject\LLM\SFT\data\databases\store_1.sqlite"


def _find_aliases(tree):
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
    s = sql.strip().rstrip(";").strip()
    if not s:
        return ""
    try:
        tree = sqlglot.parse_one(s, dialect="mysql").copy()
    except Exception:
        return s.upper()
    alias_map = _find_aliases(tree)
    
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
    
    def strip_aliases(node):
        if isinstance(node, exp.Alias):
            return node.this.copy()
        return node
    tree = tree.transform(strip_aliases)
    
    def remove_explicit_asc(node):
        if isinstance(node, exp.Ordered):
            desc = node.args.get("desc")
            if desc is False:
                node.args.pop("desc", None)
        return node
    tree = tree.transform(remove_explicit_asc)
    
    return tree.sql(dialect="mysql", pretty=False)


def ast_equal(gold: str, gen: str) -> bool:
    if not gold or not gen:
        return False
    return normalize_sql(gold) == normalize_sql(gen)


def execute_equal(gold: str, gen: str) -> bool:
    """Execute both SQLs against SQLite and compare results."""
    try:
        conn = sqlite3.connect(DB_PATH)
        g_result = conn.execute(gold).fetchall()
        gen_result = conn.execute(gen).fetchall()
        conn.close()
        return sorted(g_result) == sorted(gen_result)
    except Exception:
        return False


def compare(gold: str, gen: str) -> bool:
    """Compare: try AST first, then execution validation."""
    if ast_equal(gold, gen):
        return True
    # AST failed, try execution-based comparison
    if gen and gen != "ERROR" and not gen.startswith("ERROR:"):
        if execute_equal(gold, gen):
            return True
    return False


# Load results
results = [json.loads(l) for l in open('reports/eval_store_1.jsonl', 'r', encoding='utf-8')]
print(f"{'AST':>5} {'Exec':>5} {'Final':>5} | Query")
print("-" * 75)

correct_ast = 0
correct_exec = 0
correct_final = 0

for r in results:
    a = ast_equal(r['gold'], r['generated'])
    e = False
    if not a and r['generated'] and not r['generated'].startswith("ERROR"):
        e = execute_equal(r['gold'], r['generated'])
    f = a or e
    
    if a: correct_ast += 1
    if e: correct_exec += 1
    if f: correct_final += 1
    
    ast_s = "AST" if a else ""
    exec_s = "+EX" if e else ""
    fin_s = "OK" if f else "XX"
    print(f"{ast_s:>5} {exec_s:>5} {fin_s:>5} | {r['query'][:45]}")

print(f"\nAST match:      {correct_ast}/{len(results)} = {correct_ast/len(results)*100:.1f}%")
print(f"Exec additional: +{correct_exec}")
print(f"Final accuracy:  {correct_final}/{len(results)} = {correct_final/len(results)*100:.1f}%")
print()
print("Breakdown of saved-by-execution:")
for r in results:
    a = ast_equal(r['gold'], r['generated'])
    e = False
    if not a and r['generated'] and not r['generated'].startswith("ERROR"):
        e = execute_equal(r['gold'], r['generated'])
    if not a and e:
        print(f"  + {r['query'][:50]}")
        print(f"    Gold: {r['gold'][:60]}")
        print(f"    Gen:  {r['generated'][:60]}")
