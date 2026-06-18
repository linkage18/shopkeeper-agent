"""
Report 路由 — SSE 流式报告生成
"""
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.auth.middleware import require_user
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.report_agent.planner import plan_report
from app.report_agent.executor import execute_sqls, execute_python, generate_report_text
from app.report_agent.renderer import build_chart_data
from app.schema_analyzer.analyzer import get_schema as get_db_schema
from app.core.log import logger

report_agent_router = APIRouter(prefix="/api/report", tags=["report"])


class ReportReq(BaseModel):
    query: str


async def _generate(query: str, user_id: str):
    """报告生成管线 — 逐步推送 SSE"""
    try:
        # 1. 读取 Schema
        async with dw_mysql_client_manager.session_factory() as session:
            schema = await get_db_schema(session)
            schema_text = json.dumps(schema, ensure_ascii=False, indent=2)[:3000]

        yield f"data: {json.dumps({'type': 'progress', 'step': '读取数据库结构', 'status': 'success'}, ensure_ascii=False)}\n\n"

        # 2. 规划
        plan = await plan_report(query, schema_text)
        sqls = plan.get("sqls", [])
        python_code = plan.get("python_preprocess", "")
        chart_info = {
            "chart_type": plan.get("chart_type", "bar"),
            "chart_title": plan.get("chart_title", "分析图表"),
        }
        yield f"data: {json.dumps({'type': 'progress', 'step': '计划模式', 'status': 'success', 'detail': plan}, ensure_ascii=False)}\n\n"

        # 3. 执行 SQL
        async with dw_mysql_client_manager.session_factory() as session:
            sql_results = await execute_sqls(sqls, session)

        for sql_id, data in sql_results.items():
            if sql_id.endswith("_error"):
                yield f"data: {json.dumps({'type': 'result', 'sql_id': sql_id, 'error': data}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'result', 'sql_id': sql_id, 'data': data[:50]}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'progress', 'step': 'SQL 查询完成', 'status': 'success'}, ensure_ascii=False)}\n\n"

        # 4. Python 预处理
        if python_code:
            python_results = await execute_python(python_code, sql_results)
            yield f"data: {json.dumps({'type': 'progress', 'step': '数据处理', 'status': 'success', 'python_results': python_results}, ensure_ascii=False)}\n\n"
        else:
            python_results = {}

        # 5. 图表
        main_data = None
        for sql_def in sqls:
            data = sql_results.get(sql_def["id"], [])
            if data:
                main_data = data
                break
        chart_data = None
        if main_data:
            chart_data = build_chart_data(main_data, chart_info)
            if chart_data:
                yield f"data: {json.dumps({'type': 'result', 'chart_data': chart_data}, ensure_ascii=False)}\n\n"

        # 6. 报告文本
        report_text = await generate_report_text(query, sql_results, python_results or {}, chart_info)
        yield f"data: {json.dumps({'type': 'result', 'report_md': report_text}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'progress', 'step': '完成', 'status': 'success'}, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(f"Report 生成失败: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'报告生成失败: {str(e)}'}, ensure_ascii=False)}\n\n"


@report_agent_router.post("/generate")
async def generate_report(req: ReportReq, user: Annotated[dict, Depends(require_user)]):
    return StreamingResponse(
        _generate(req.query, user.get("user_id", "")),
        media_type="text/event-stream",
    )
