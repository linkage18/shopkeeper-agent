from __future__ import annotations
import os
from pathlib import Path

import yaml

TEMPLATES_DIR = Path(__file__).parent / "templates"
_cache: dict[str, dict] = {}


class ParamValidationError(ValueError):
    """参数验证失败"""
    pass


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


def _validate_param(value, param_def: dict) -> str:
    """验证并转换单个参数值，防止 SQL 注入

    规则：
    - type: select → value 必须在 param_def['options'] 中
    - type: int → value 必须能转换为 int
    - type: float → value 必须能转换为 float
    - type: str → 转义单引号
    """
    param_type = param_def.get("type", "str")
    name = param_def["name"]

    if param_type == "select":
        options = param_def.get("options", [])
        str_val = str(value)
        if str_val not in options:
            raise ParamValidationError(
                f"参数 '{name}' 值 '{str_val}' 不在允许列表中: {options}"
            )
        return str_val

    elif param_type == "int":
        try:
            int_val = int(value)
        except (ValueError, TypeError) as e:
            raise ParamValidationError(
                f"参数 '{name}' 需要 int 类型，收到: {value!r}"
            ) from e
        return str(int_val)

    elif param_type == "float":
        try:
            float_val = float(value)
        except (ValueError, TypeError) as e:
            raise ParamValidationError(
                f"参数 '{name}' 需要 float 类型，收到: {value!r}"
            ) from e
        return str(float_val)

    else:
        # type: str — 默认字符串类型，转义单引号防止注入
        str_val = str(value)
        escaped = str_val.replace("'", "''")
        return escaped


def render_sql(template: dict, params: dict) -> list[dict]:
    """验证参数并渲染 SQL 模板

    所有参数在注入 SQL 模板前都经过类型校验和转义，
    防止恶意参数值构造 SQL 注入攻击。
    """
    # 构建参数定义索引
    param_defs: dict[str, dict] = {}
    for param_def in template.get("params", []):
        name = param_def["name"]
        param_defs[name] = param_def

    # 填充默认值并验证所有参数
    validated: dict[str, str] = {}
    for param_def in template.get("params", []):
        name = param_def["name"]
        raw_value = params.get(name, param_def.get("default"))
        if raw_value is None:
            raise ParamValidationError(
                f"缺少必需参数 '{name}'"
            )
        validated[name] = _validate_param(raw_value, param_def)

    # 拒绝未在模板中定义的参数
    unknown_params = set(params.keys()) - set(param_defs.keys())
    if unknown_params:
        raise ParamValidationError(
            f"存在未定义的参数: {unknown_params}"
        )

    rendered = []
    for sql_def in template.get("sqls", []):
        sql_text = sql_def["sql"]
        for k, v in validated.items():
            placeholder = "{" + k + "}"
            sql_text = sql_text.replace(placeholder, v)
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
