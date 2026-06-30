"""长期记忆 — 结构化知识定义

每次读取都从 MD 文件重新加载，不做内存缓存。

目录结构：
  data/knowledge/shared/definitions/  — 业务口径定义
  data/knowledge/shared/metrics/       — 指标说明
  data/knowledge/shared/mappings/      — 同义词映射
  data/knowledge/private/{uid}/        — 用户私有
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.core.log import logger
from app.core.md_parser import parse_knowledge_md

SHARED_DIRS = [
    Path("data/knowledge/shared/definitions"),
    Path("data/knowledge/shared/metrics"),
    Path("data/knowledge/shared/mappings"),
]


async def _parse_md(fp: Path) -> dict[str, Any] | None:
    try:
        text = await asyncio.to_thread(lambda: fp.read_text(encoding="utf-8"))
        return parse_knowledge_md(text, fp.stem)
    except Exception as e:
        logger.debug(f"parse_md failed: {fp.name} - {e}")
        return None


async def search_long_term(query: str, user_id: str = "") -> list[dict]:
    """全文搜索长期记忆，返回匹配条目（异步，不阻塞 event loop）"""
    results: list[dict] = []
    seen: set[str] = set()

    # 搜索共享目录
    for base_dir in SHARED_DIRS:
        if not base_dir.exists():
            continue
        for fp in base_dir.glob("*.md"):
            text = await asyncio.to_thread(lambda: fp.read_text(encoding="utf-8"))
            if query.lower() not in text.lower():
                continue
            parsed = await _parse_md(fp)
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
                text = await asyncio.to_thread(lambda: fp.read_text(encoding="utf-8"))
                if query.lower() not in text.lower():
                    continue
                parsed = await _parse_md(fp)
                if parsed and fp.stem not in seen:
                    seen.add(fp.stem)
                    parsed["scope"] = "private"
                    parsed["category"] = "private"
                    results.append(parsed)

    return results[:10]


async def get_long_term_context(query: str, user_id: str = "") -> str:
    """获取长期记忆上下文文本，拼入 system prompt"""
    entries = await search_long_term(query, user_id)
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
