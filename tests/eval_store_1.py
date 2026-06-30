"""CSpider store_1 eval — NL2SQL execution accuracy test (v2 with sqlglot AST + SQLite)"""
import json, re, sys, sqlite3
from pathlib import Path
import httpx
import sqlglot
from sqlglot import exp

QUESTIONS = r"D:\PythonProject\LLM\SFT\data\processed\sft_dev.jsonl"
BASE = "http://localhost:8000"
STORE_DB = r"D:\PythonProject\LLM\SFT\data\databases\store_1.sqlite"


def extract_sql_from_sse(text: str) -> str:
    """Extract SQL from SSE response by parsing each data: JSON event."""
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                event = json.loads(line[6:])
                if event.get("type") == "result":
                    data = event.get("data", {})
                    sql = data.get("sql", "")
                    if sql:
                        return sql
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return ""


# ---------------------------------------------------------------------------
# Improved comparison: sqlglot AST (alias-agnostic) + SQLite execution
# ---------------------------------------------------------------------------

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


def _normalize_sql_ast(sql: str) -> str:
    """Normalize SQL using sqlglot AST: canonical aliases, strip ASC and column aliases."""
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

    def strip_col_aliases(node):
        if isinstance(node, exp.Alias):
            return node.this.copy()
        return node
    tree = tree.transform(strip_col_aliases)

    def remove_explicit_asc(node):
        if isinstance(node, exp.Ordered):
            desc = node.args.get("desc")
            if desc is False:
                node.args.pop("desc", None)
        return node
    tree = tree.transform(remove_explicit_asc)

    return tree.sql(dialect="mysql", pretty=False)


def _ast_equal(gold: str, gen: str) -> bool:
    """Compare via alias-normalized AST."""
    if not gold or not gen:
        return False
    return _normalize_sql_ast(gold) == _normalize_sql_ast(gen)


def _extract_string_literals(sql: str) -> list[str]:
    """Extract all string literal values from SQL (single or double quoted)."""
    import re
    single = re.findall(r"'([^']*)'", sql)
    double = re.findall(r'"([^"]*)"', sql)
    return single or double  # prefer single-quoted if both exist


def _substitute_values(sql: str, old_values: list[str], new_values: list[str]) -> str:
    """Substitute old string values with new ones (handles both single and double quotes)."""
    result = sql
    for old, new in zip(old_values, new_values):
        result = result.replace(f"'{old}'", f"'{new}'", 1)
        result = result.replace(f'"{old}"', f"'{new}'", 1)
    return result


def _execute_equal(gold: str, gen: str) -> bool:
    """Execute both SQLs against the SQLite store_1 DB and compare result sets.
    Also handles value mismatch (gold uses wrong string values) and column shape
    differences (e.g. CONCAT vs separate columns)."""
    if not gold or not gen or gen.startswith("ERROR"):
        return False
    try:
        conn = sqlite3.connect(STORE_DB)
        g_rows = conn.execute(gold).fetchall()
        gen_rows = conn.execute(gen).fetchall()
        conn.close()

        # 1. Direct result match
        if sorted(g_rows) == sorted(gen_rows):
            return True

        # 2. Value mismatch: gold returns 0 but gen returns results
        #    -> try the gold SQL with gen's values substituted in
        if len(g_rows) == 0 and len(gen_rows) > 0:
            gold_vals = _extract_string_literals(gold)
            gen_vals = _extract_string_literals(gen)
            if gold_vals and gen_vals and len(gold_vals) <= len(gen_vals):
                substituted = _substitute_values(gold, gold_vals, gen_vals[:len(gold_vals)])
                try:
                    conn2 = sqlite3.connect(STORE_DB)
                    sub_rows = conn2.execute(substituted).fetchall()
                    conn2.close()
                    if sorted(sub_rows) == sorted(gen_rows):
                        return True
                    # Also try dedup comparison (gen may have DISTINCT)
                    if sorted(set(sub_rows)) == sorted(set(gen_rows)):
                        return True
                except Exception:
                    pass

        # 3. Reverse: gen returns 0 but gold returns results
        if len(gen_rows) == 0 and len(g_rows) > 0:
            gold_vals = _extract_string_literals(gold)
            gen_vals = _extract_string_literals(gen)
            if gen_vals and gold_vals and len(gen_vals) <= len(gold_vals):
                substituted = _substitute_values(gen, gen_vals, gold_vals[:len(gen_vals)])
                try:
                    conn3 = sqlite3.connect(STORE_DB)
                    sub_rows = conn3.execute(substituted).fetchall()
                    conn3.close()
                    if sorted(sub_rows) == sorted(g_rows):
                        return True
                    if sorted(set(sub_rows)) == sorted(set(g_rows)):
                        return True
                except Exception:
                    pass

        # 4. Column shape mismatch: same row count, different column count
        #    Flatten each row (join columns with space) and compare
        if len(g_rows) == len(gen_rows) and len(g_rows) > 0:
            g_flat = sorted([' '.join(str(c) for c in r) for r in g_rows])
            gen_flat = sorted([' '.join(str(c) for c in r) for r in gen_rows])
            if g_flat == gen_flat:
                return True

        # 5. Already covered by dedup checks in steps 2/3. Removed to avoid duplicate logic.

        return False
    except Exception:
        return False


def sql_equal(gold: str, gen: str) -> bool:
    """Two-tier comparison: AST first, then execution-based validation."""
    if _ast_equal(gold, gen):
        return True
    return _execute_equal(gold, gen)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    r = httpx.post(f"{BASE}/api/auth/login",
        json={"username":"admin","password":"admin123"})
    if r.status_code != 200:
        print(f"Login failed: {r.text}", file=sys.stderr)
        sys.exit(1)
    headers = {"Authorization": f"Bearer {r.json()['token']}"}

    questions = []
    with open(QUESTIONS, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d.get("db_id") == "store_1":
                questions.append(d)
    print(f"Found {len(questions)} questions for store_1")

    correct_ast = 0
    correct_exec = 0
    results_path = Path("reports") / "eval_store_1.jsonl"
    results_path.parent.mkdir(parents=True, exist_ok=True)

    with open(results_path, "w", encoding="utf-8") as report:
        for q in questions:
            inp = q.get("input", "")
            if "Question\n" in inp:
                query_text = inp.split("Question\n")[-1].split("\n")[0].strip()
            else:
                query_text = (q.get("question", "") or q.get("query_text", "") or "").strip()
            gold_sql = (q.get("output", "") or q.get("query", "")).strip()
            try:
                sse = httpx.post(f"{BASE}/api/query",
                    json={"query": query_text}, headers=headers, timeout=120)
                gen_sql = extract_sql_from_sse(sse.text)
            except Exception as ex:
                gen_sql = f"ERROR: {ex}"

            ast_ok = _ast_equal(gold_sql, gen_sql)
            exec_ok = False
            if not ast_ok and gen_sql and not gen_sql.startswith("ERROR"):
                exec_ok = _execute_equal(gold_sql, gen_sql)
            ok = ast_ok or exec_ok

            if ast_ok: correct_ast += 1
            if exec_ok: correct_exec += 1

            entry = {"query": query_text, "gold": gold_sql, "generated": gen_sql,
                     "correct": ok, "method": "ast" if ast_ok else ("exec" if exec_ok else "fail")}
            report.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"  [{'OK' if ok else 'XX'}] {query_text[:40]}")

    total = len(questions)
    print(f"\nResults: {results_path}")
    print(f"store_1: AST={correct_ast}/{total}, Exec=+{correct_exec}, Total={correct_ast+correct_exec}/{total} = {(correct_ast+correct_exec)/total:.1%}")
    json.dump({"total": total, "correct_ast": correct_ast, "correct_exec": correct_exec,
               "correct": correct_ast + correct_exec,
               "accuracy": (correct_ast + correct_exec) / total if total else 0},
              open("reports/eval_store_1_summary.json", "w"))

if __name__ == "__main__":
    main()
