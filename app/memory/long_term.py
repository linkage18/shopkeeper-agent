"""
长期记忆 — 结构化知识定义
每次读取都从 MD 文件重新加载，不做内存缓存。

目录结构：
  data/knowledge/shared/definitions/  — 业务口径定义
  data/knowledge/shared/metrics/      — 指标说明
  data/knowledge/shared/mappings/     — 同义词映射
  data/knowledge/private/{uid}/       — 用户私有
"""
import re
from pathlib import Path
from typing import Any

from app.core.log import logger

SHARED_DIRS = [
    Path("data/knowledge/shared/definitions"),
    Path("data/knowledge/shared/metrics"),
    Path("data/knowledge/shared/mappings"),
]


def _parse_md(fp: Path) -> dict[str, Any] | None:
    try:
        text = fp.read_text(encoding="utf-8")
        title = fp.stem
        def_match = re.search(r"## 定义\n(.+?)(?:\n##|\Z)", text, re.DOTALL)
        definition = def_match.group(1).strip() if def_match else ""
        tables_match = re.search(r"## 涉及表\n(.+?)(?:\n##|\Z)", text, re.DOTALL)
        tables = []
        if tables_match:
            for line in tables_match.group(1).strip().split("\n"):
                line = line.strip().strip("- ").strip()
                if line:
                    tables.append(line)
        sql_match = re.search(r"```sql\n(.+?)\n```", text, re.DOTALL)
        example_sql = sql_match.group(1).strip() if sql_match else ""
        tags_match = re.search(r"## 标签\n\[(.+?)\]", text)
        tags = [t.strip() for t in tags_match.group(1).split(",")] if tags_match else []
        status_match = re.search(r"审核状态：(.+)", text)
        status = status_match.group(1).strip() if status_match else "approved"
        return {
            "title": title,
            "definition": definition,
            "tables": tables,
            "example_sql": example_sql,
            "tags": tags,
            "status": status,
        }
    except Exception as e:
        logger.debug(f"parse_md failed: {fp.name} - {e}")
        return None


def search_long_term(query: str, user_id: str = "") -> list[dict]:
    """全文搜索长期记忆，返回匹配条目"""
    results = []
    seen = set()

    # 搜索共享目录
    for base_dir in SHARED_DIRS:
        if not base_dir.exists():
            continue
        for fp in base_dir.glob("*.md"):
            text = fp.read_text(encoding="utf-8")
            if query.lower() not in text.lower():
                continue
            parsed = _parse_md(fp)
            if parsed and fp.stem not in seen:
                seen.add(fp.stem)
                parsed["scope"] = "shared"
                parsed["category"] = base_dir.name
                results.append(parsed)

    # 搜索私有目录
    if user_id:
        private_dir = Path(f"data/knowledge/private/{user_id}")
        if private_dir.exists():
            for fp in private_dir.glob("*.md"):
                text = fp.read_text(encoding="utf-8")
                if query.lower() not in text.lower():
                    continue
                parsed = _parse_md(fp)
                if parsed and fp.stem not in seen:
                    seen.add(fp.stem)
                    parsed["scope"] = "private"
                    parsed["category"] = "private"
                    results.append(parsed)

    return results[:10]


def get_long_term_context(query: str, user_id: str = "") -> str:
    """获取长期记忆上下文文本，拼入 system prompt"""
    entries = search_long_term(query, user_id)
    if not entries:
        return ""
    parts = []
    for e in entries:
        if e.get("status") != "approved":
            continue
        parts.append(
            f"【{e['title']}】\n"
            f"定义：{e['definition']}\n"
            f"涉及表：{', '.join(e['tables'])}\n"
            f"示例SQL：{e['example_sql']}"
        )
    return "\n\n".join(parts)
