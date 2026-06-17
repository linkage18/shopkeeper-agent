import os
import re
from pathlib import Path
from typing import List

from app.knowledge.models import KnowledgeEntry

SHARED_DIR = Path("data/knowledge/shared")
PRIVATE_DIR = Path("data/knowledge/private")


def _parse_md(file_path: Path) -> KnowledgeEntry | None:
    try:
        text = file_path.read_text(encoding="utf-8")
        title = file_path.stem
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
        return KnowledgeEntry(
            title=title, definition=definition, tables=tables,
            example_sql=example_sql, tags=tags, status=status,
        )
    except Exception:
        return None


def list_knowledge(is_admin: bool = False, user_id: str = "") -> list[dict]:
    results = []
    if SHARED_DIR.exists():
        for f in sorted(SHARED_DIR.iterdir()):
            if f.suffix == ".md":
                entry = _parse_md(f)
                if entry:
                    results.append({"id": f.stem, "title": entry.title, "tags": entry.tags, "status": entry.status, "scope": "shared"})
    if user_id:
        user_dir = PRIVATE_DIR / user_id
        if user_dir.exists():
            for f in sorted(user_dir.iterdir()):
                if f.suffix == ".md":
                    entry = _parse_md(f)
                    if entry:
                        results.append({"id": f.stem, "title": entry.title, "tags": entry.tags, "status": entry.status, "scope": "private"})
    return results


def get_knowledge(title: str, user_id: str = "") -> KnowledgeEntry | None:
    for base_dir in [SHARED_DIR, PRIVATE_DIR / user_id] if user_id else [SHARED_DIR]:
        fp = base_dir / f"{title}.md"
        if fp.exists():
            return _parse_md(fp)
    return None


def save_knowledge(entry: KnowledgeEntry, user_id: str, is_shared: bool = True):
    base_dir = SHARED_DIR if is_shared else PRIVATE_DIR / user_id
    base_dir.mkdir(parents=True, exist_ok=True)
    fp = base_dir / f"{entry.title}.md"
    tables_section = "\n".join(f"- {t}" for t in entry.tables) if entry.tables else "无"
    tags_str = ", ".join(entry.tags)
    content = (
        f"# {entry.title}\n\n"
        f"## 定义\n{entry.definition}\n\n"
        f"## 涉及表\n{tables_section}\n\n"
        f"## 示例SQL\n```sql\n{entry.example_sql}\n```\n\n"
        f"## 标签\n[{tags_str}]\n\n"
        f"## 元数据\n"
        f"- 创建时间：{entry.created_at}\n"
        f"- 创建者：{entry.created_by}\n"
        f"- 审核状态：{entry.status}\n"
    )
    fp.write_text(content, encoding="utf-8")


def delete_knowledge(title: str, user_id: str, is_shared: bool):
    base_dir = SHARED_DIR if is_shared else PRIVATE_DIR / user_id
    fp = base_dir / f"{title}.md"
    if fp.exists():
        fp.unlink()
        return True
    return False


def search_knowledge(query: str, user_id: str = "") -> list[dict]:
    results = []
    for base_dir in [SHARED_DIR, PRIVATE_DIR / user_id] if user_id else [SHARED_DIR]:
        if not base_dir.exists():
            continue
        for f in base_dir.iterdir():
            if f.suffix != ".md":
                continue
            text = f.read_text(encoding="utf-8")
            if query.lower() in text.lower():
                entry = _parse_md(f)
                if entry:
                    results.append({"id": f.stem, "title": entry.title, "tags": entry.tags, "scope": "shared" if base_dir == SHARED_DIR else "private"})
    return results
