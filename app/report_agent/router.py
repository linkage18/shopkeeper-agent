"""
Report 路由 — SSE 流式报告生成
"""
import json
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.auth.middleware import require_user
from app.clients.mysql_client_manager import dw_mysql_client_manager
from app.report_agent.planner import plan_report
from app.report_agent.executor import execute_sqls, execute_python, generate_report_text
from app.report_agent.renderer import build_chart_data
from app.schema_analyzer.analyzer import get_schema as get_db_schema
from app.core.log import logger

report_agent_router = APIRouter(prefix="/api/report", tags=["report"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class ReportReq(BaseModel):
    query: str


async def _generate(query: str, user_id: str):
    """报告生成管线 — 逐步推送 SSE"""
    try:
        # 1. 读取 Schema 并构建清晰的字段名索引
        yield _sse({"type": "progress", "step": "读取 Schema", "status": "running"})
        async with dw_mysql_client_manager.session_factory() as session:
            schema = await get_db_schema(session)
            # 构建字段名索引：每张表 + 字段名 + 字段描述
            field_index_parts = ["可用字段列表："]
            for t in schema.get("tables", []):
                field_index_parts.append(f"\n表 {t['name']} ({t['role']}):")
                for c in t["columns"]:
                    desc = f" ({c['comment']})" if c["comment"] else ""
                    field_index_parts.append(f"  - {c['name']}  [{c['type']}]  {c['role']}{desc}")
            field_index = "\n".join(field_index_parts)
            # 完整 schema 不截断
            schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
            # 限制总长度但保留字段名索引（最后 3000 字符）
            if len(schema_text) > 6000:
                schema_text = schema_text[:3000] + "\n...\n" + field_index[:3000]

        yield _sse({"type": "progress", "step": "读取 Schema", "status": "success"})

        # 2. 规划
        yield _sse({"type": "progress", "step": "规划报告", "status": "running"})
        plan = await plan_report(query, schema_text)
        sqls = plan.get("sqls", [])
        python_code = plan.get("python_preprocess", "")
        chart_info = {
            "chart_type": plan.get("chart_type", "bar"),
            "chart_title": plan.get("chart_title", "分析图表"),
        }
        yield _sse({"type": "progress", "step": "规划报告", "status": "success", "detail": plan})

        # 3. 执行 SQL
        yield _sse({"type": "progress", "step": "执行 SQL", "status": "running"})
        async with dw_mysql_client_manager.session_factory() as session:
            sql_results = await execute_sqls(sqls, session)

        for sql_id, data in sql_results.items():
            if sql_id.endswith("_error"):
                yield _sse({"type": "result", "sql_id": sql_id, "error": data})
            else:
                yield _sse({"type": "result", "sql_id": sql_id, "data": data[:50]})

        yield _sse({"type": "progress", "step": "执行 SQL", "status": "success"})

        # 4. Python 预处理
        yield _sse({"type": "progress", "step": "数据处理", "status": "running"})
        if python_code:
            python_results = await execute_python(python_code, sql_results)
        else:
            python_results = {}
        yield _sse({"type": "progress", "step": "数据处理", "status": "success", "python_results": python_results})

        # 5. 图表
        yield _sse({"type": "progress", "step": "构建图表", "status": "running"})
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
                yield _sse({"type": "result", "chart_data": chart_data})
        yield _sse({"type": "progress", "step": "构建图表", "status": "success"})

        # 6. 报告文本
        yield _sse({"type": "progress", "step": "生成报告", "status": "running"})
        report_text = await generate_report_text(query, sql_results, python_results or {}, chart_info)
        yield _sse({"type": "result", "report_md": report_text})
        yield _sse({"type": "progress", "step": "生成报告", "status": "success"})

        yield _sse({"type": "progress", "step": "完成", "status": "success"})

    except Exception as e:
        logger.error(f"Report 生成失败: {e}")
        yield _sse({"type": "error", "message": f"报告生成失败: {str(e)}"})


@report_agent_router.post("/generate")
async def generate_report(req: ReportReq, user: Annotated[dict, Depends(require_user)]):
    return StreamingResponse(
        _generate(req.query, user.get("user_id", "")),
        media_type="text/event-stream",
    )
