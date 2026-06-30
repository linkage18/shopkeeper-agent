import os
from pathlib import Path
from typing import List

from app.core.md_parser import parse_knowledge_md
from app.knowledge.models import KnowledgeEntry

SHARED_DIR = Path("data/knowledge/shared")
PRIVATE_DIR = Path("data/knowledge/private")


def _parse_md(file_path: Path) -> KnowledgeEntry | None:
    try:
        text = file_path.read_text(encoding="utf-8")
        parsed = parse_knowledge_md(text, file_path.stem)
        if parsed is None:
            return None
        return KnowledgeEntry(
            title=parsed["title"], definition=parsed["definition"],
            tables=parsed["tables"], example_sql=parsed["example_sql"],
            tags=parsed["tags"], status=parsed["status"],
        )
    except Exception as e:
        from app.core.log import logger
        logger.warning(f"Failed to parse knowledge md {file_path.name}: {e}")
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
