"""短期记忆 — 当前会话上下文

每次读取都从 JSONL 文件重新加载，不做内存缓存。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

SESSIONS_DIR = Path("data/sessions")


async def get_session_history(session_id: str, max_rounds: int = 6) -> list[dict]:
    """读取指定会话的最近 N 轮对话（异步，不阻塞 event loop）"""
    fp = SESSIONS_DIR / f"{session_id}.jsonl"
    if not fp.exists():
        return []
    text = await asyncio.to_thread(lambda: fp.read_text(encoding="utf-8"))
    lines = text.strip().split("\n")
    history = []
    for line in lines:
        if line.strip():
            try:
                history.append(json.loads(line))
            except Exception:
                from app.core.log import logger
                logger.warning("Failed to parse history line")
                continue
    return history[-max_rounds * 2:] if history else []


async def get_session_summary(session_id: str) -> str:
    """读取会话摘要"""
    history = await get_session_history(session_id, max_rounds=1)
    if history:
        return history[-1].get("summary", "")
    return ""


async def get_recent_context(session_id: str, query: str = "") -> str:
    """获取短期记忆上下文文本，拼入 system prompt"""
    history = await get_session_history(session_id)
    if not history:
        return ""
    lines = []
    for msg in history[-4:]:  # 最近 4 条
        role = "用户" if msg.get("role") == "user" else "助手"
        lines.append(f"{role}: {msg.get('content', msg.get('answer', ''))[:200]}")
    return "\n".join(lines)
