import json
import sqlite3
import sys
import re
from pathlib import Path
DB_DIR = r"D:\PythonProject\LLM\SFT\data\databases"
TYPE_MAP = {"number": "FLOAT", "text": "VARCHAR(255)", "time": "DATETIME"}
def load_schema(db_id):
    tables_path = Path(r"D:\PythonProject\LLM\SFT\data\raw\cspider") / "tables.json"
    tables = json.load(open(tables_path, encoding="utf-8"))
    for t in tables:
        if t["db_id"] == db_id:
            return t
    return None
def gen_ddl(schema, with_data=True):
    lines = ["CREATE DATABASE IF NOT EXISTS dw DEFAULT CHARACTER SET utf8mb4;", "USE dw;"]
    for i, tn in enumerate(schema["table_names_original"]):
        if tn == "sqlite_sequence": continue
        col_idxs = [schema["column_names_original"].index(c) for c in schema["column_names_original"] if c[0] == i]
        cols = [(schema["column_names_original"][ci][1], TYPE_MAP.get(schema["column_types"][ci], "VARCHAR(255)")) for ci in col_idxs]
        if not cols: continue
        col_defs = ", ".join(f"`{n}` {t}" for n, t in cols)
        pks = [n for n, t in cols if n.lower().endswith("_id") or n.lower() == "id"]
        if pks: col_defs += ", PRIMARY KEY (`" + pks[0] + "`)"
        lines.append(f"\nDROP TABLE IF EXISTS `{tn}`;")
        lines.append(f"CREATE TABLE `{tn}` ({col_defs});")
        if not with_data: continue
        conn = sqlite3.connect(str(Path(DB_DIR) / "store_1.sqlite"))
        cur = conn.cursor()
        try:
            cur.execute(f'SELECT * FROM "' + tn + '"')
            rows = cur.fetchall()
            if rows:
                cnames = ", ".join("`" + schema["column_names_original"][ci][1] + "`" for ci in col_idxs)
                lines.append(f"INSERT INTO `{tn}` ({cnames}) VALUES")
                for ri, row in enumerate(rows):
                    vals = []
                    for v in row:
                        if v is None: vals.append("NULL")
                        elif isinstance(v, str): vals.append("'" + v.replace("'", "\\'") + "'")
                        else: vals.append(str(v))
                    comma = "," if ri < len(rows) - 1 else ";"
                    lines.append("  (" + ", ".join(vals) + ")" + comma)
        except Exception as ex:
            print(f"WARN: {tn}: {ex}", file=sys.stderr)
        conn.close()
    return "\n".join(lines)
def gen_yaml(schema):
    lines = ["tables:"]
    for i, tn in enumerate(schema["table_names_original"]):
        if tn == "sqlite_sequence": continue
        is_fact = any(k in tn.lower() for k in ["order","invoice","line","item"])
        lines.append("  - name: " + tn)
        lines.append("    role: " + ("fact" if is_fact else "dim"))
        lines.append("    description: " + tn.lower().replace("_"," "))
        lines.append("    columns:")
        for c in schema["column_names_original"]:
            if c[0] != i: continue
            ci = schema["column_names_original"].index(c)
            ct = TYPE_MAP.get(schema["column_types"][ci], "VARCHAR(255)")
            n = c[1]
            sync = "true" if any(k in n.lower() for k in ["name","code","type","genre","city","state","country","company"]) else "false"
            if n.lower().endswith("_id"):
                r = "primary_key" if n.lower().startswith("id") else "foreign_key"
            elif any(k in n.lower() for k in ["price","total","amount","quantity","milliseconds","bytes"]):
                r = "measure"
            else:
                r = "dimension"
            lines.append("      - name: " + n)
            lines.append("        role: " + r)
            lines.append("        type: " + ct)
            lines.append("        description: " + n.lower().replace("_"," "))
            lines.append("        alias: [" + n.lower() + "]")
            lines.append("        sync: " + sync)
    lines.append("")
    lines.append("metrics:")
    lines.append("  - name: total_revenue")
    lines.append("    description: total revenue from all invoices")
    lines.append("    relevant_columns:")
    lines.append("      - invoices.total")
    lines.append("    alias: [revenue, total sales, income]")
    lines.append("  - name: avg_unit_price")
    lines.append("    description: average unit price of tracks")
    lines.append("    relevant_columns:")
    lines.append("      - tracks.unit_price")
    lines.append("    alias: [avg price, average price]")
    return "\n".join(lines)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["schema","ddl","yaml","all"], default="all")
    args = parser.parse_args()
    s = load_schema("store_1")
    if not s:
        print("Schema not found", file=sys.stderr)
        sys.exit(1)
    if args.mode == "schema":
        for i, tn in enumerate(s["table_names_original"]):
            if tn == "sqlite_sequence": continue
            cols = [c[1] for c in s["column_names_original"] if c[0] == i]
            print(f"  {tn}: {', '.join(cols)}")
    elif args.mode == "ddl":
        result = gen_ddl(s, with_data=False)
        sys.stdout.write(result)
    elif args.mode == "yaml":
        sys.stdout.write(gen_yaml(s))
    elif args.mode == "all":
        result = gen_ddl(s, with_data=True)
        sys.stdout.write(result)
        sys.stdout.write("\n-- YAML CONFIG --\n")
        sys.stdout.write(gen_yaml(s))
