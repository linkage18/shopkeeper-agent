"""
Report Executor — 执行 SQL + Python 预处理
"""
import json
from typing import Any, AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.report_agent.sandbox import run_pandas, SandboxError
from app.core.log import logger


async def execute_sqls(sqls: list[dict], dw_session: AsyncSession) -> dict[str, list[dict]]:
    """逐条执行 SQL，返回 {sql_id: [rows]}"""
    results = {}
    for sql_def in sqls:
        try:
            rows = []
            result = await dw_session.execute(text(sql_def["sql"]))
            for row in result.mappings().fetchall():
                rows.append(dict(row))
            results[sql_def["id"]] = rows
        except Exception as e:
            logger.error(f"SQL 执行失败 [{sql_def['id']}]: {e}")
            results[sql_def["id"]] = []
            results[f"{sql_def['id']}_error"] = str(e)
    return results


async def execute_python(code: str, sql_results: dict[str, list[dict]]) -> dict[str, Any]:
    """执行 Python 预处理代码"""
    if not code or not code.strip():
        return {}
    # 将 SQL 结果转成 DataFrame
    import pandas as pd
    data_frames = {}
    for k, v in sql_results.items():
        if k.endswith("_error"):
            continue
        data_frames[k] = pd.DataFrame(v)
    try:
        result = run_pandas(code, data_frames)
        return result
    except SandboxError as e:
        logger.error(f"Python 沙箱错误: {e}")
        return {"_error": str(e)}


async def generate_report_text(query: str, sql_results: dict, python_results: dict, chart_info: dict) -> str:
    """LLM 根据所有结果生成最终报告"""
    from app.agent.llm import llm

    context_parts = [f"用户问题：{query}\n"]
    for k, v in sql_results.items():
        if k.endswith("_error"):
            context_parts.append(f"[SQL 错误 - {k}]: {v}\n")
        else:
            context_parts.append(f"[SQL 结果 - {k}]: {json.dumps(v, ensure_ascii=False)[:500]}\n")
    if python_results:
        context_parts.append(f"[Python 处理结果]: {json.dumps(python_results, ensure_ascii=False)[:300]}\n")
    if chart_info:
        context_parts.append(f"[图表类型]: {chart_info.get('chart_type', '')} — {chart_info.get('chart_title', '')}\n")

    prompt = (
        "你是一个数据分析报告撰写专家。根据以下数据分析结果，生成一份 Markdown 格式的分析报告。\n"
        "要求：结论清晰、数据支撑、有条理。包括概述、分析正文、结论建议。\n\n"
        + "\n".join(context_parts) +
        "\n请生成完整的 Markdown 报告："
    )
    resp = await llm.ainvoke(prompt)
    return resp.strip()
