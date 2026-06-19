"""
Schema & Viz 路由 — 动态可视化 API
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.middleware import require_user
from app.clients.mysql_client_manager import dw_mysql_client_manager
from app.schema_analyzer.analyzer import get_schema as get_db_schema
from app.report_agent.renderer import build_chart_data
from app.core.log import logger

schema_router = APIRouter(prefix="/api/schema", tags=["schema"])
viz_router = APIRouter(prefix="/api/viz", tags=["viz"])

# SQL 缓存：{(dimensions+measures+chart_type) → sql_text}
_sql_cache: dict[str, str] = {}



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
        cache_key = f"viz|{sorted(req.dimensions)}|{sorted(req.measures)}|{req.chart_type}"

        # SQL 缓存命中则跳过 LLM
        if cache_key in _sql_cache:
            sql_text = _sql_cache[cache_key]
            logger.info(f"[VIZ] SQL 缓存命中: {cache_key[:60]}")
        else:
            async with dw_mysql_client_manager.session_factory() as session:
                schema = await get_db_schema(session)

            # 用 LLM 生成 SQL（仅在首次）
            tables_info = []
            for t in schema.get("tables", []):
                cols = ", ".join(c["name"] for c in t["columns"])
                tables_info.append(f"{t['name']}({t['role']}): {cols}")
            schema_desc = "\n".join(tables_info)

            prompt = (
                f"根据数据库结构和用户选择，生成一条 SQL 查询。\n\n"
                f"数据库表结构：\n{schema_desc}\n\n"
                f"选择维度：{dim_str}\n"
                f"选择指标：{mea_str}\n"
                f"图表类型：{req.chart_type}\n\n"
                f"输出纯 SQL，不要 markdown 代码块。注意多表 JOIN 和 GROUP BY。"
            )
            from app.agent.llm import llm
            sql_text = await llm.ainvoke(prompt)
            sql_text = sql_text.strip().strip("```sql").strip("```").strip()
            _sql_cache[cache_key] = sql_text
            logger.info(f"[VIZ] SQL 生成完成，已缓存")

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
