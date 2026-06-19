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

    def summarize_rows(rows: list[dict], max_rows: int = 20) -> dict[str, Any]:
        if not rows:
            return {"row_count": 0, "sample_rows": []}
        sample_rows = rows[:max_rows]
        numeric_summary: dict[str, dict[str, float]] = {}
        keys = rows[0].keys() if isinstance(rows[0], dict) else []
        for key in keys:
            vals = [row.get(key) for row in rows if isinstance(row.get(key), (int, float))]
            if vals:
                numeric_summary[key] = {
                    "sum": round(float(sum(vals)), 4),
                    "avg": round(float(sum(vals) / len(vals)), 4),
                    "max": round(float(max(vals)), 4),
                    "min": round(float(min(vals)), 4),
                }
        return {
            "row_count": len(rows),
            "sample_rows": sample_rows,
            "numeric_summary": numeric_summary,
        }

    context_parts = [f"用户问题：{query}\n"]
    for k, v in sql_results.items():
        if k.endswith("_error"):
            context_parts.append(f"[SQL 错误 - {k}]: {v}\n")
        else:
            summary = summarize_rows(v if isinstance(v, list) else [])
            context_parts.append(f"[SQL 结果 - {k}]: {json.dumps(summary, ensure_ascii=False)[:2500]}\n")
    if python_results:
        context_parts.append(f"[Python 处理结果]: {json.dumps(python_results, ensure_ascii=False)[:300]}\n")
    if chart_info:
        context_parts.append(f"[图表类型]: {chart_info.get('chart_type', '')} — {chart_info.get('chart_title', '')}\n")

    prompt = (
        "你是一个严谨的数据分析师。请根据 SQL 结果生成一份可直接给业务人员阅读的 Markdown 报告。\n"
        "必须遵守：\n"
        "1. 不编造没有出现在数据里的结论。\n"
        "2. 先给核心结论，再展开数据分析。\n"
        "3. 每个重要判断都要带具体数值或排序依据。\n"
        "4. 如果数据不足，明确写出数据不足，而不是强行总结。\n"
        "5. 不输出代码块。\n\n"
        "报告结构：\n"
        "# 标题\n"
        "## 核心结论\n"
        "用 3 条以内 bullet 总结。\n"
        "## 数据概览\n"
        "说明查询行数、时间范围或统计口径。\n"
        "## 详细分析\n"
        "结合维度、指标、排名、占比或变化趋势展开。\n"
        "## 业务建议\n"
        "给出 2-3 条可执行建议。\n"
        "## 附录\n"
        "说明图表类型和异常/限制。\n\n"
        + "\n".join(context_parts) +
        "\n请生成完整报告："
    )
    resp = await llm.ainvoke(prompt)
    return resp.content.strip()
