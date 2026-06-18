from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.middleware import require_user
from app.clients.mysql_client_manager import dw_mysql_client_manager
from app.reports.executor import list_templates, load_template, render_sql
from app.reports.renderer import generate_chart, build_report
from app.reports.miner import extract_knowledge_from_report
from app.core.log import logger

reports_router = APIRouter(prefix="/api/reports", tags=["reports"])


class AnalysisReq(BaseModel):
    template_id: str
    params: dict[str, Any]


class AnalysisResp(BaseModel):
    template_id: str
    params: dict[str, Any]
    chart_b64: str | None = None
    report_md: str
    results: dict[str, Any]


@reports_router.get("/templates")
async def get_templates(user: Annotated[dict, Depends(require_user)]):
    return {"templates": list_templates()}


@reports_router.get("/templates/{template_id}")
async def get_template(template_id: str, user: Annotated[dict, Depends(require_user)]):
    tmpl = load_template(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"template": tmpl}


@reports_router.post("/analyze", response_model=AnalysisResp)
async def analyze(req: AnalysisReq, user: Annotated[dict, Depends(require_user)]):
    tmpl = load_template(req.template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 1. 渲染 SQL
    sqls = render_sql(tmpl, req.params)

    # 2. 逐条执行
    results: dict[str, list[dict]] = {}
    async with dw_mysql_client_manager.session_factory() as session:
        from sqlalchemy import text
        for sql_def in sqls:
            try:
                rows = []
                result = await session.execute(text(sql_def["sql"]))
                for row in result.mappings().fetchall():
                    rows.append(dict(row))
                results[sql_def["id"]] = rows
            except Exception as e:
                logger.error(f"SQL执行失败 [{sql_def['id']}]: {e}")
                results[sql_def["id"]] = []
                results[f"{sql_def['id']}_error"] = str(e)

    # 3. 出图
    main_key = sqls[0]["id"] if sqls else "main"
    main_data = results.get(main_key, [])
    chart_b64 = generate_chart(main_data, tmpl.get("chart", {}), req.params)

    # 4. 生成报告
    report_md = build_report(req.params, tmpl, results, chart_b64)

    # 5. 知识挖掘（静默运行，失败不影响主流程）
    try:
        await extract_knowledge_from_report(req.params, results, user.get("user_id", ""))
    except Exception:
        pass

    return AnalysisResp(
        template_id=req.template_id,
        params=req.params,
        chart_b64=chart_b64,
        report_md=report_md,
        results=results,
    )
