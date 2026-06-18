"""
Schema & Viz 路由 — 动态可视化 API
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.middleware import require_user
from app.clients.mysql_client_manager import dw_mysql_client_manager
from app.schema_analyzer.analyzer import get_schema as get_db_schema
from app.report_agent.planner import plan_report
from app.report_agent.executor import execute_sqls, execute_python
from app.report_agent.renderer import build_chart_data
from app.core.log import logger

schema_router = APIRouter(prefix="/api/schema", tags=["schema"])
viz_router = APIRouter(prefix="/api/viz", tags=["viz"])


class VizReq(BaseModel):
    dimensions: list[str]       # 用户选择的维度字段
    measures: list[str]         # 用户选择的指标字段
    chart_type: str = "bar"     # bar / line / pie
    filters: dict[str, Any] = {}  # 过滤条件
    limit: int = 50


class VizResp(BaseModel):
    chart_data: dict[str, Any] | None = None
    table_data: list[dict[str, Any]] = []
    sql: str = ""
    error: str = ""


@schema_router.get("")
async def get_schema(user: Annotated[dict, Depends(require_user)]):
    async with dw_mysql_client_manager.session_factory() as session:
        schema = await get_db_schema(session)
    return schema


@viz_router.post("/generate", response_model=VizResp)
async def generate_viz(req: VizReq, user: Annotated[dict, Depends(require_user)]):
    """根据用户选择的维度和指标，自动生成 SQL + 执行 + 返回图表数据"""
    try:
        dim_str = ", ".join(req.dimensions)
        mea_str = ", ".join(req.measures)
        # 自动确定表和 JOIN 关系
        async with dw_mysql_client_manager.session_factory() as session:
            schema = await get_db_schema(session)
            schema_str = str(schema)[:2000]

        # 用 LLM 生成 SQL
        prompt = (
            f"根据数据库结构和用户选择，生成一条 SQL 查询。\n\n"
            f"数据库结构：{schema_str}\n\n"
            f"选择维度：{dim_str}\n"
            f"选择指标：{mea_str}\n"
            f"图表类型：{req.chart_type}\n\n"
            f"输出纯 SQL，不要 markdown 代码块。注意多表 JOIN 和 GROUP BY。"
        )
        from app.agent.llm import llm
        sql_text = await llm.ainvoke(prompt)
        sql_text = sql_text.strip().strip("```sql").strip("```").strip()

        # 执行 SQL
        async with dw_mysql_client_manager.session_factory() as session:
            from sqlalchemy import text
            result = await session.execute(text(sql_text))
            rows = [dict(row) for row in result.mappings().fetchall()]

        if not rows:
            return VizResp(error="查询结果为空")

        # 构建图表数据
        chart_info = {"chart_type": req.chart_type, "chart_title": f"{dim_str} × {mea_str}"}
        chart_data = build_chart_data(rows, chart_info)

        return VizResp(chart_data=chart_data, table_data=rows[:req.limit], sql=sql_text)

    except Exception as e:
        logger.error(f"Viz 生成失败: {e}")
        return VizResp(error=str(e))
