"""
CSpider NL2SQL 评估脚本

支持两种评估模式:
  --mode direct   : 直接向 LLM 发送含 Schema 的提示词（默认，测试 SQL 生成能力）
  --mode pipeline : 通过项目的完整检索管线（需要知识库已构建 + 服务运行中）

用法:
  # 测试单个数据库
  python scripts/eval_cspider.py --db-id store_1
  python scripts/eval_cspider.py --db-id academic --mode pipeline

  # 测试全部数据库（仅 direct 模式）
  python scripts/eval_cspider.py --db-id all --limit 500

  # 指定 CSpider 数据目录
  python scripts/eval_cspider.py --db-id store_1 --cspider-dir /path/to/SFT/data
"""
import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Optional

import yaml

CONF_DIR = Path("conf/cspider")
DEFAULT_CSPIDER_DIR = Path(r"D:\PythonProject\LLM\SFT\data")
REPORT_DIR = Path("reports")

TYPE_MAP_REVERSE = {"FLOAT": "number", "VARCHAR(255)": "text", "DATETIME": "time"}


# ===================================================================
# Schema Helpers
# ===================================================================

def load_yaml_schema(db_id: str) -> dict | None:
    """从 YAML 配置加载 CSpider 数据库 Schema"""
    path = CONF_DIR / f"{db_id}.yaml"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def format_schema_prompt(schema: dict) -> str:
    """把 YAML schema 格式化为 LLM 友好的提示词块"""
    parts = ["### Database Schema\n"]
    for tbl in schema.get("tables", []):
        cols = []
        for col in tbl.get("columns", []):
            parts.append(f"  - {col['name']}  [{col['type']}]  {col['role']}")
            if col.get("description"):
                parts[-1] += f"  ({col['description']})"
        cols_str = "\n".join(cols) if cols else "  (no columns)"
        parts.append(f"\nCREATE TABLE {tbl['name']} (\n{cols_str}\n);\n")
    return "\n".join(parts)


def collect_original_schema(cspider_dir: Path, db_id: str) -> dict | None:
    """从 CSpider 的 tables.json 读取原始 schema（含原始列名/类型）"""
    tables_path = cspider_dir / "raw" / "cspider" / "tables.json"
    if not tables_path.exists():
        return None
    tables = json.loads(tables_path.read_text(encoding="utf-8"))
    for t in tables:
        if t["db_id"] == db_id:
            return t
    return None


# ===================================================================
# SQLite Execution
# ===================================================================

def _extract_string_literals(sql: str) -> list[str]:
    single = re.findall(r"'([^']*)'", sql)
    double = re.findall(r'"([^"]*)"', sql)
    return single or double


def _substitute_values(sql: str, old_values: list[str], new_values: list[str]) -> str:
    result = sql
    for old, new in zip(old_values, new_values):
        result = result.replace(f"'{old}'", f"'{new}'", 1)
        result = result.replace(f'"{old}"', f"'{new}'", 1)
    return result


def execute_sql(sqlite_path: Path, sql: str) -> list[tuple]:
    """在 SQLite 数据库上执行 SQL 并返回所有行"""
    if not sqlite_path.exists():
        return []
    conn = sqlite3.connect(str(sqlite_path))
    try:
        rows = conn.execute(sql).fetchall()
        return rows
    finally:
        conn.close()


def compare_results(gold: str, gen: str, sqlite_path: Optional[Path]) -> bool:
    """通过 SQLite 执行比较两个 SQL 的结果集"""
    if not gold or not gen or gen.startswith("ERROR"):
        return False

    try:
        g_rows = execute_sql(sqlite_path, gold)
        gen_rows = execute_sql(sqlite_path, gen)

        # 1. 直接排序比较
        if sorted(g_rows) == sorted(gen_rows):
            return True

        # 2. 空结果修复（gold 用 gen 的值替换）
        if len(g_rows) == 0 and len(gen_rows) > 0:
            gold_vals = _extract_string_literals(gold)
            gen_vals = _extract_string_literals(gen)
            if gold_vals and gen_vals and len(gold_vals) <= len(gen_vals):
                substituted = _substitute_values(gold, gold_vals, gen_vals[:len(gold_vals)])
                try:
                    sub_rows = execute_sql(sqlite_path, substituted)
                    if sorted(sub_rows) == sorted(gen_rows):
                        return True
                    if sorted(set(sub_rows)) == sorted(set(gen_rows)):
                        return True
                except Exception:
                    pass

        # 3. 反向修复（gen 用 gold 的值替换）
        if len(gen_rows) == 0 and len(g_rows) > 0:
            gold_vals = _extract_string_literals(gold)
            gen_vals = _extract_string_literals(gen)
            if gen_vals and gold_vals and len(gen_vals) <= len(gold_vals):
                substituted = _substitute_values(gen, gen_vals, gold_vals[:len(gen_vals)])
                try:
                    sub_rows = execute_sql(sqlite_path, substituted)
                    if sorted(sub_rows) == sorted(g_rows):
                        return True
                    if sorted(set(sub_rows)) == sorted(set(g_rows)):
                        return True
                except Exception:
                    pass

        # 4. 列数不匹配但行数匹配（如 CONCAT vs 分开的列）
        if len(g_rows) == len(gen_rows) and len(g_rows) > 0:
            g_flat = sorted([" ".join(str(c) for c in r) for r in g_rows])
            gen_flat = sorted([" ".join(str(c) for c in r) for r in gen_rows])
            if g_flat == gen_flat:
                return True

        return False
    except Exception:
        return False


# ===================================================================
# LLM-based Direct Evaluation
# ===================================================================

async def eval_direct(question: dict, schema: dict, llm) -> dict:
    """直接调用 LLM 生成 SQL（不经过检索管线）"""
    schema_text = format_schema_prompt(schema)
    db_id = question.get("db_id", "unknown")
    query_text = _extract_question(question)
    gold_sql = (question.get("output", "") or question.get("query", "")).strip()

    prompt = (
        "你是一个 SQL 生成助手。根据数据库 Schema 和用户问题，生成对应的 SQL 查询语句。\n"
        "只输出一条可执行的 SQL 语句，不要解释、注释或 Markdown 代码块标记。\n\n"
        f"用户问题：{query_text}\n\n"
        f"{schema_text}\n\n"
        "SQL："
    )

    t0 = time.time()
    try:
        resp = await llm.ainvoke(prompt)
        gen_sql = resp.content.strip()
        # Clean markdown code blocks
        if gen_sql.startswith("```"):
            gen_sql = re.sub(r"^```(?:sql)?\s*", "", gen_sql)
            gen_sql = re.sub(r"\s*```$", "", gen_sql)
        gen_sql = gen_sql.strip()
    except Exception as e:
        gen_sql = f"ERROR: {e}"
    elapsed = time.time() - t0

    return {
        "query": query_text,
        "gold": gold_sql,
        "generated": gen_sql,
        "db_id": db_id,
        "difficulty": question.get("difficulty", "unknown"),
        "latency": round(elapsed, 2),
    }


def _extract_question(question: dict) -> str:
    """从 SFT 格式的 question 中提取用户问题文本"""
    inp = question.get("input", "")
    if "Question\n" in inp:
        return inp.split("Question\n")[-1].split("\n")[0].strip()
    return (question.get("question", "") or question.get("query_text", "") or "").strip()


# ===================================================================
# SSE pipeline eval (from existing eval_store_1.py)
# ===================================================================

def extract_sql_from_sse(text: str) -> str:
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


async def eval_pipeline(question: dict, base_url: str, headers: dict) -> dict:
    """通过项目的 /api/query 管线评估"""
    import httpx
    db_id = question.get("db_id", "unknown")
    query_text = _extract_question(question)
    gold_sql = (question.get("output", "") or question.get("query", "")).strip()

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{base_url}/api/query",
                json={"query": query_text},
                headers=headers,
            )
        gen_sql = extract_sql_from_sse(resp.text) or "ERROR: no SQL in SSE response"
    except Exception as e:
        gen_sql = f"ERROR: {e}"
    elapsed = time.time() - t0

    return {
        "query": query_text,
        "gold": gold_sql,
        "generated": gen_sql,
        "db_id": db_id,
        "difficulty": question.get("difficulty", "unknown"),
        "latency": round(elapsed, 2),
    }


# ===================================================================
# Main Eval Loop
# ===================================================================

def _find_sqlite_db(cspider_dir: Path, db_id: str, external_fallback: Path = Path(r"D:\PythonProject\LLM\SFT\data")) -> Optional[Path]:
    """查找 SQLite 数据库文件（支持项目内和外部目录）"""
    candidates = [
        cspider_dir / "databases" / f"{db_id}.sqlite",
        external_fallback / "databases" / f"{db_id}.sqlite",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


async def main():
    parser = argparse.ArgumentParser(description="CSpider NL2SQL 评估工具")
    parser.add_argument("--db-id", default="all", help="数据库 ID 或 'all'")
    parser.add_argument("--mode", choices=["direct", "pipeline"], default="direct",
                        help="评估模式: direct(直接LLM) / pipeline(全管线)")
    parser.add_argument("--cspider-dir", default=str(DEFAULT_CSPIDER_DIR),
                        help="CSpider 数据集根目录")
    parser.add_argument("--limit", type=int, default=0,
                        help="每个数据库最多评估的问题数（0=全部）")
    parser.add_argument("--base-url", default="http://localhost:8000",
                        help="pipeline 模式用的 API 地址")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--output", default="reports/cspider_eval.jsonl",
                        help="评估结果输出文件")
    args = parser.parse_args()

    cspider_dir = Path(args.cspider_dir)

    # Fallback: 如果外部目录不可用，使用项目内的 data/cspider
    dev_path = cspider_dir / "processed" / "sft_dev.jsonl"
    if not dev_path.exists():
        fallback = Path("data/cspider") / "sft_dev.jsonl"
        if fallback.exists():
            print(f"Note: using fallback directory: data/cspider")
            cspider_dir = Path("data/cspider")
            dev_path = fallback
    if not dev_path.exists():
        print(f"Error: SFT dev file not found in {cspider_dir}", file=sys.stderr)
        sys.exit(1)

    report_path = REPORT_DIR / Path(args.output).name
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    all_questions: list[dict] = []
    with open(dev_path, encoding="utf-8") as f:
        for line in f:
            all_questions.append(json.loads(line))
    print(f"Loaded {len(all_questions)} dev questions total")

    # ── 筛选目标数据库 ──
    if args.db_id == "all":
        db_ids = sorted(set(q.get("db_id", "") for q in all_questions if q.get("db_id")))
        target_questions = all_questions
    else:
        db_ids = [args.db_id]
        target_questions = [q for q in all_questions if q.get("db_id") == args.db_id]

    print(f"Target databases: {len(db_ids)}, questions: {len(target_questions)}")
    if args.limit > 0:
        target_questions = target_questions[:args.limit]
        print(f"Limited to {args.limit} questions")

    # ── 初始化 ──
    if args.mode == "direct":
        from app.agent.llm import get_llm
        llm = get_llm()

    if args.mode == "pipeline":
        import httpx
        r = httpx.post(f"{args.base_url}/api/auth/login",
                        json={"username": args.username, "password": args.password})
        if r.status_code != 200:
            print(f"Login failed: {r.text}", file=sys.stderr)
            sys.exit(1)
        token = r.json().get("token") or r.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}
    else:
        headers = {}

    # ── 执行评估 ──
    results: list[dict] = []
    correct = 0
    total = 0

    for q in target_questions:
        db_id = q.get("db_id", "")
        if not db_id:
            continue

        # 加载 schema
        if args.mode == "direct":
            schema = load_yaml_schema(db_id)
            if not schema:
                print(f"  [SKIP] No YAML schema for {db_id}")
                continue
            result = await eval_direct(q, schema, llm)
        else:
            result = await eval_pipeline(q, args.base_url, headers)

        # 执行比较
        sqlite_path = _find_sqlite_db(cspider_dir, db_id)
        gen = result["generated"]
        gold = result["gold"]

        if not sqlite_path:
            result["correct"] = False
            result["method"] = "no_db"
        elif gen.startswith("ERROR"):
            result["correct"] = False
            result["method"] = "error"
        elif compare_results(gold, gen, sqlite_path):
            result["correct"] = True
            result["method"] = "exec"
        else:
            result["correct"] = False
            result["method"] = "fail"

        results.append(result)
        total += 1
        if result["correct"]:
            correct += 1

        status = "OK" if result["correct"] else "XX"
        print(f"  [{status}] {db_id}: {result['query'][:50]}")

    # ── 输出结果 ──
    with open(report_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nResults saved to {report_path}")

    # ── 汇总报告 ──
    accuracy = correct / total if total else 0
    print(f"\n{'='*60}")
    print(f"Total: {correct}/{total} = {accuracy:.1%}")

    # 按数据库汇总
    print(f"\n{'='*60}")
    print("By database:")
    by_db: dict[str, dict] = {}
    for r in results:
        db = r["db_id"]
        if db not in by_db:
            by_db[db] = {"correct": 0, "total": 0}
        by_db[db]["total"] += 1
        if r["correct"]:
            by_db[db]["correct"] += 1
    for db in sorted(by_db.keys()):
        d = by_db[db]
        acc = d["correct"] / d["total"] if d["total"] else 0
        print(f"  {db}: {d['correct']}/{d['total']} = {acc:.1%}")

    # 按难度汇总
    print(f"\nBy difficulty:")
    by_diff: dict[str, dict] = {}
    for r in results:
        diff = r.get("difficulty", "unknown")
        if diff not in by_diff:
            by_diff[diff] = {"correct": 0, "total": 0}
        by_diff[diff]["total"] += 1
        if r["correct"]:
            by_diff[diff]["correct"] += 1
    for diff in sorted(by_diff.keys()):
        d = by_diff[diff]
        acc = d["correct"] / d["total"] if d["total"] else 0
        print(f"  {diff}: {d['correct']}/{d['total']} = {acc:.1%}")

    # 生成 summary JSON
    summary = {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "mode": args.mode,
        "by_database": {k: {"correct": v["correct"], "total": v["total"]} for k, v in sorted(by_db.items())},
        "by_difficulty": {k: {"correct": v["correct"], "total": v["total"]} for k, v in sorted(by_diff.items())},
    }
    summary_path = REPORT_DIR / "cspider_eval_summary.json"
    json.dump(summary, open(summary_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nSummary saved to {summary_path}")

    # top-N 错误分析
    errors = [r for r in results if not r["correct"]]
    if errors:
        print(f"\nTop error examples ({min(5, len(errors))} of {len(errors)}):")
        for e in errors[:5]:
            print(f"  DB={e['db_id']} | Q: {e['query'][:60]}")
            print(f"    Gold: {e['gold'][:80]}")
            print(f"    Gen:  {e['generated'][:80]}")
            print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
