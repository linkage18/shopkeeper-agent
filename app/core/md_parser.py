"""共享 MD 知识文件解析工具

统一 long_term.py 和 knowledge/manager.py 中的 MD 解析逻辑。
"""
from __future__ import annotations

import re
from typing import Any, Optional


def parse_knowledge_md(text: str, title: str) -> Optional[dict[str, Any]]:
    """解析知识库 MD 文本内容，返回结构化字段

    返回 dict 包含: title, definition, tables, example_sql, tags, status
    解析失败返回 None。
    """
    try:
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
    except Exception:
        return None
