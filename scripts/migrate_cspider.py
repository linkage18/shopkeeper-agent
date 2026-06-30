"""
CSpider 数据库迁移工具

为 CSpider 数据集中任意数据库生成 YAML 元数据配置，供知识库构建管线（Qdrant + ES）使用。

用法:
  python scripts/migrate_cspider.py --db-id store_1
  python scripts/migrate_cspider.py --db-id all
  python scripts/migrate_cspider.py --db-id all --cspider-dir /path/to/SFT/data
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# CSpider 类型 → MySQL 类型映射
# ---------------------------------------------------------------------------
TYPE_MAP = {"number": "FLOAT", "text": "VARCHAR(255)", "time": "DATETIME"}


# ---------------------------------------------------------------------------
# CSpider tables.json 字段属性检测
# ---------------------------------------------------------------------------
def _is_primary_key(name: str) -> bool:
    return name.lower() in ("id",) or name.lower().endswith("id") and len(name) <= 6


def _is_foreign_key(name: str) -> bool:
    return name.lower().endswith("_id") and not _is_primary_key(name)


def _is_measure(name: str, type_str: str) -> bool:
    name_lower = name.lower()
    if name_lower in ("id",) or name_lower.endswith("_id"):
        return False
    return type_str == "number" and any(
        k in name_lower for k in ["price", "total", "amount", "quantity",
                                   "milliseconds", "bytes", "score", "rate",
                                   "salary", "budget", "cost", "fee", "count",
                                   "pop", "area", "size", "stabb", "gdp",
                                   "number", "year", "pop"]
    )


def _is_fact_table(name: str) -> bool:
    return any(k in name.lower() for k in ["order", "invoice", "line", "item",
                                            "record", "log", "transaction",
                                            "payment", "shipment", "enrollment",
                                            "registration", "purchase", "sale",
                                            "rental", "reservation"])


def _should_sync(name: str) -> bool:
    """决定字段值是否同步到 ES（仅对可枚举的维度字段同步）"""
    return any(k in name.lower() for k in ["name", "code", "type", "genre",
                                            "city", "state", "country", "company",
                                            "category", "status", "gender",
                                            "color", "language", "currency"])


# ---------------------------------------------------------------------------
# YAML 生成
# ---------------------------------------------------------------------------
def gen_yaml_config(schema: dict) -> str:
    """为单个 CSpider 数据库生成 YAML 元数据配置"""
    lines = ["tables:"]
    db_id = schema["db_id"]

    for i, tn in enumerate(schema["table_names_original"]):
        if tn == "sqlite_sequence":
            continue
        is_fact = _is_fact_table(tn)
        lines.append(f'  - name: "{tn}"')
        lines.append(f"    role: {'fact' if is_fact else 'dim'}")
        desc = tn.lower().replace("_", " ")
        lines.append(f'    description: "{desc}"')
        lines.append("    columns:")
        col_idxs = [ci for ci, c in enumerate(schema["column_names_original"]) if c[0] == i]
        for ci in col_idxs:
            col_name = schema["column_names_original"][ci][1]
            col_type = TYPE_MAP.get(schema["column_types"][ci], "VARCHAR(255)")
            sync = _should_sync(col_name)
            if _is_primary_key(col_name):
                role = "primary_key"
            elif _is_foreign_key(col_name):
                role = "foreign_key"
            elif _is_measure(col_name, schema["column_types"][ci]):
                role = "measure"
            else:
                role = "dimension"
            lines.append(f'      - name: "{col_name}"')
            lines.append(f"        role: {role}")
            lines.append(f"        type: {col_type}")
            desc = col_name.lower().replace("_", " ")
            lines.append(f'        description: "{desc}"')
            lines.append(f"        alias: [\"{col_name.lower()}\"]")
            lines.append(f"        sync: {'true' if sync else 'false'}")

    # ── metrics ──
    lines.append("")
    lines.append("metrics:")
    measure_count = 0
    for i, tn in enumerate(schema["table_names_original"]):
        if tn == "sqlite_sequence":
            continue
        col_idxs = [ci for ci, c in enumerate(schema["column_names_original"]) if c[0] == i]
        for ci in col_idxs:
            col_name = schema["column_names_original"][ci][1]
            if _is_measure(col_name, schema["column_types"][ci]):
                metric_name = f"{tn.lower()}_{col_name.lower()}"
                lines.append(f'  - name: "{metric_name}"')
                lines.append(f"    description: {col_name.lower().replace('_', ' ')} from {tn.lower()}")
                lines.append("    relevant_columns:")
                lines.append(f"      - {tn}.{col_name}")
                lines.append(f"    alias: [{col_name.lower()}]")
                measure_count += 1
    if measure_count == 0:
        lines.pop()  # remove empty metrics header
        del lines[-1]  # remove blank line before metrics

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SQL DDL 生成
# ---------------------------------------------------------------------------
def gen_ddl(schema: dict, db_id: str, cspider_dir: Path, with_data: bool = False) -> str:
    """为单个 CSpider 数据库生成 MySQL DDL"""
    lines = [
        f"-- CSpider: {db_id}",
        f"SET NAMES utf8mb4;",
    ]

    for i, tn in enumerate(schema["table_names_original"]):
        if tn == "sqlite_sequence":
            continue
        col_idxs = [ci for ci, c in enumerate(schema["column_names_original"]) if c[0] == i]
        cols = [
            (
                schema["column_names_original"][ci][1],
                TYPE_MAP.get(schema["column_types"][ci], "VARCHAR(255)"),
            )
            for ci in col_idxs
        ]
        if not cols:
            continue
        col_defs = ", ".join(f"`{n}` {t}" for n, t in cols)
        pks = [n for n, t in cols if n.lower().endswith("_id") or n.lower() == "id"]
        if pks:
            col_defs += ", PRIMARY KEY (`" + pks[0] + "`)"
        lines.append(f"\nDROP TABLE IF EXISTS `{db_id}_{tn}`;")
        lines.append(f"CREATE TABLE `{db_id}_{tn}` ({col_defs});")

        if with_data:
            db_path = cspider_dir / "databases" / f"{db_id}.sqlite"
            if not db_path.exists():
                continue
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            try:
                cur.execute(f'SELECT * FROM "{tn}"')
                rows = cur.fetchall()
                if rows:
                    cnames = ", ".join(
                        f"`{schema['column_names_original'][ci][1]}`" for ci in col_idxs
                    )
                    lines.append(f"INSERT INTO `{db_id}_{tn}` ({cnames}) VALUES")
                    for ri, row in enumerate(rows):
                        vals = []
                        for v in row:
                            if v is None:
                                vals.append("NULL")
                            elif isinstance(v, str):
                                vals.append("'" + v.replace("'", "\\'") + "'")
                            else:
                                vals.append(str(v))
                        comma = "," if ri < len(rows) - 1 else ";"
                        lines.append("  (" + ", ".join(vals) + ")" + comma)
            except Exception as ex:
                print(f"  [WARN] {tn}: {ex}", file=sys.stderr)
            conn.close()

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 批量 YAML 生成（所有数据库）
# ---------------------------------------------------------------------------
def batch_generate(cspider_dir: Path, output_dir: Path):
    """为 CSpider 数据集中所有数据库生成 YAML 元数据配置"""
    tables_path = _find_tables_json(cspider_dir)
    if not tables_path:
        print(f"Error: tables.json not found in {cspider_dir}", file=sys.stderr)
        return
    tables = json.loads(tables_path.read_text(encoding="utf-8"))
    print(f"Found {len(tables)} databases in tables.json")

    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for schema in tables:
        db_id = schema["db_id"]
        yaml_text = gen_yaml_config(schema)
        out_path = output_dir / f"{db_id}.yaml"
        out_path.write_text(yaml_text, encoding="utf-8")
        print(f"  [OK] {db_id} -> {out_path}")
        count += 1
    print(f"\nGenerated {count} YAML configs in {output_dir}")


# ---------------------------------------------------------------------------
# DDL 批量生成
# ---------------------------------------------------------------------------
def batch_ddl(cspider_dir: Path, output_dir: Path):
    """为所有 CSpider 数据库生成 DDL"""
    tables_path = _find_tables_json(cspider_dir)
    if not tables_path:
        print(f"Error: tables.json not found in {cspider_dir}", file=sys.stderr)
        return
    tables = json.loads(tables_path.read_text(encoding="utf-8"))

    output_dir.mkdir(parents=True, exist_ok=True)
    for schema in tables:
        db_id = schema["db_id"]
        ddl = gen_ddl(schema, db_id, cspider_dir, with_data=False)
        out_path = output_dir / f"{db_id}.sql"
        out_path.write_text(ddl, encoding="utf-8")
        print(f"  [OK] {db_id}.sql -> {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="CSpider 数据库迁移工具")
    parser.add_argument("--db-id", default="all",
                        help="Database ID (e.g. store_1) 或 'all' 处理全部 (default: all)")
    parser.add_argument("--cspider-dir",
                        default=r"D:\PythonProject\LLM\SFT\data",
                        help="CSpider 数据集根目录")
    parser.add_argument("--output-dir", default="conf/cspider",
                        help="YAML 配置文件输出目录 (default: conf/cspider)")
    parser.add_argument("--ddl-dir", default="docker/mysql/cspider",
                        help="DDL SQL 输出目录 (default: docker/mysql/cspider)")
    parser.add_argument("--mode", choices=["yaml", "ddl", "all"], default="yaml",
                        help="生成模式: yaml / ddl / all (default: yaml)")
    parser.add_argument("--with-data", action="store_true",
                        help="DDL 中包含 INSERT 数据")
    args = parser.parse_args()

    cspider_dir = Path(args.cspider_dir)
    # Fallback: 如果外部目录不可用，使用项目内的 data/cspider
    if not _find_tables_json(cspider_dir):
        fallback = Path("data/cspider")
        if _find_tables_json(fallback):
            print(f"Note: using fallback directory: {fallback}")
            cspider_dir = fallback
    if not _find_tables_json(cspider_dir):
        print(f"Error: tables.json not found in {cspider_dir} (nor in data/cspider)", file=sys.stderr)
        sys.exit(1)

    if args.db_id == "all":
        if args.mode in ("yaml", "all"):
            batch_generate(cspider_dir, Path(args.output_dir))
        if args.mode in ("ddl", "all"):
            batch_ddl(cspider_dir, Path(args.ddl_dir))
    else:
        schema = load_schema(cspider_dir, args.db_id)
        if not schema:
            print(f"Error: Database '{args.db_id}' not found in tables.json", file=sys.stderr)
            sys.exit(1)

        if args.mode in ("yaml", "all"):
            yaml_text = gen_yaml_config(schema)
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{args.db_id}.yaml"
            out_path.write_text(yaml_text, encoding="utf-8")
            print(f"YAML config written to {out_path}")

        if args.mode in ("ddl", "all"):
            ddl = gen_ddl(schema, args.db_id, cspider_dir, with_data=args.with_data)
            ddl_dir = Path(args.ddl_dir)
            ddl_dir.mkdir(parents=True, exist_ok=True)
            out_path = ddl_dir / f"{args.db_id}.sql"
            out_path.write_text(ddl, encoding="utf-8")
            if args.with_data:
                print(f"DDL (with data) written to {out_path}")
            else:
                print(f"DDL (schema only) written to {out_path}")


def load_schema(cspider_dir: Path, db_id: str) -> Optional[dict]:
    tables_path = _find_tables_json(cspider_dir)
    if not tables_path:
        return None
    tables = json.loads(tables_path.read_text(encoding="utf-8"))
    for t in tables:
        if t["db_id"] == db_id:
            return t
    return None


def _find_tables_json(cspider_dir: Path) -> Optional[Path]:
    """查找 tables.json（支持外部目录和项目内 data/cspider 两种结构）"""
    candidates = [
        cspider_dir / "raw" / "cspider" / "tables.json",
        cspider_dir / "tables.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


if __name__ == "__main__":
    main()
