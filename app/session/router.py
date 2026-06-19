"""
Session 保存路由 — 用于保存 NL2SQL 等非 RAG 的对话历史
"""
from __future__ import annotations
from typing import Annotated, Any
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.middleware import require_user

session_router = APIRouter(prefix="/api/session", tags=["session"])


class SessionRecord(BaseModel):
    query: str
    answer: str = ""
    summary: str = ""
    type: str = "sql"
    chart_data: dict[str, Any] | None = None
    data: list[dict[str, Any]] | None = None
    row_count: int = 0


def _json_default(obj):
    from decimal import Decimal
    from datetime import date, datetime as dt
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, dt)):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    return str(obj)


@session_router.post("/save")
async def save_session(record: SessionRecord, user: Annotated[dict, Depends(require_user)]):
    """保存一条对话记录到会话文件"""
    sessions_dir = Path("data/sessions")
    sessions_dir.mkdir(parents=True, exist_ok=True)
    user_id = user.get("user_id", "anonymous")[:8]
    prefix = "rpt" if record.type == "report" else "sql"
    session_id = f"{prefix}_{user_id}_{datetime.now().strftime('%Y%m%d')}"
    fp = sessions_dir / f"{session_id}.jsonl"

    entry = {
        "timestamp": datetime.now().timestamp(),
        "query": record.query,
        "answer": record.answer,
        "summary": record.summary or record.query[:60],
        "type": record.type,
        "user_id": user_id,
        "chart_data": record.chart_data,
        "data": record.data,
        "row_count": record.row_count,
    }
    with open(fp, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=_json_default) + "\n")

    return {"status": "ok", "session_id": session_id}
