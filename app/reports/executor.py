from __future__ import annotations
import os
from pathlib import Path

import yaml

TEMPLATES_DIR = Path(__file__).parent / "templates"
_cache: dict[str, dict] = {}


def list_templates() -> list[dict]:
    results = []
    for f in sorted(TEMPLATES_DIR.glob("*.yaml")):
        tmpl = load_template(f.stem)
        if tmpl:
            results.append({
                "id": f.stem,
                "name": tmpl.get("name", f.stem),
                "label": tmpl.get("label", f.stem),
                "description": tmpl.get("description", ""),
                "params": tmpl.get("params", []),
            })
    return results


def load_template(template_id: str) -> dict | None:
    if template_id in _cache:
        return _cache[template_id]
    fp = TEMPLATES_DIR / f"{template_id}.yaml"
    if not fp.exists():
        return None
    with open(fp, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _cache[template_id] = data
    return data


def render_sql(template: dict, params: dict) -> list[dict]:
    # 用模板默认值填充缺失的参数
    full_params = dict(params)
    for param_def in template.get("params", []):
        name = param_def["name"]
        if name not in full_params and "default" in param_def:
            full_params[name] = param_def["default"]

    rendered = []
    for sql_def in template.get("sqls", []):
        sql_text = sql_def["sql"]
        for k, v in full_params.items():
            placeholder = "{" + k + "}"
            sql_text = sql_text.replace(placeholder, str(v))
        rendered.append({"id": sql_def["id"], "sql": sql_text})
    return rendered


def _format_value(val) -> str:
    if val is None:
        return ""
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def build_markdown_table(rows: list[dict]) -> str:
    if not rows or not isinstance(rows[0], dict):
        return "无数据"
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(_format_value(row.get(h, "")) for h in headers) + " |")
    return "\n".join(lines)
