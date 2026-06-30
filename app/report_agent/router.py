"""
Report 路由 — SSE 流式报告生成（薄包装层）
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.auth.middleware import require_user
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.report_agent.pipeline import ReportPipeline

report_agent_router = APIRouter(prefix="/api/report", tags=["report"])


class ReportReq(BaseModel):
    query: str


async def _generate(query: str, user_id: str):
    pipeline = ReportPipeline(dw_mysql_client_manager, meta_mysql_client_manager)
    async for event in pipeline.run(query):
        yield event


@report_agent_router.post("/generate")
async def generate_report(req: ReportReq, user: Annotated[dict, Depends(require_user)]):
    return StreamingResponse(
        _generate(req.query, user.get("user_id", "")),
        media_type="text/event-stream",
    )
