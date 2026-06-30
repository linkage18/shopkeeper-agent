"""
Report Executor — 执行 SQL + Python 预处理
"""
import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.report_agent.sandbox import run_pandas, SandboxError
from app.core.log import logger


_COMMON_FIELD_FIXES = {
    "amount": "order_amount",
    "quantity": "order_quantity",
    "sales_amount": "order_amount",
    "sale_amount": "order_amount",
    "revenue": "order_amount",
    "price": "order_amount",
    "total_price": "order_amount",
    "order_count": "count",
    "qty": "order_quantity",
    "id": "order_id",
    "date": "date_id",
}


async def _llm_correct_sql(failed_sql: str, error_msg: str, schema_text: str) -> str | None:
    """用 LLM 根据错误信息修正 SQL"""
    from app.agent.llm import get_llm
    prompt = (
        "你是一个 SQL 专家。以下 SQL 执行失败，请根据错误信息和数据库 Schema 修正它。\n"
        "只输出修正后的 SQL，不要 markdown 代码块，不要任何解释。\n\n"
        f"失败的 SQL：\n{failed_sql}\n\n"
        f"错误信息：\n{error_msg}\n\n"
        f"数据库 Schema：\n{schema_text[:2000]}\n\n"
        "修正后的 SQL："
    )
    try:
        resp = await get_llm().ainvoke(prompt)
        fixed = resp.content.strip()
        if fixed.startswith("```"):
            fixed = fixed.split("\n", 1)[1] if "\n" in fixed else fixed[3:]
            fixed = fixed.rsplit("```", 1)[0] if "```" in fixed else fixed
        fixed = fixed.strip()
        if not fixed or "SELECT" not in fixed.upper():
            logger.warning(f"[LLM-RETRY] LLM 返回的不是有效 SQL: {fixed[:100]}")
            return None
        logger.info(f"[LLM-RETRY] LLM 修正成功: {fixed[:120]}...")
        return fixed
    except Exception as e:
        logger.warning(f"[LLM-RETRY] LLM 调用失败: {e}")
        return None


async def _retry_sql(failed_sql: str, error_msg: str, dw_session: AsyncSession, schema_text: str = "") -> str | None:
    """检测列名错误后自动修正并重试 — 快速路径(硬替换) → LLM 路径"""
    # 快速路径：只处理 "Unknown column" 错误，用硬替换
    if "Unknown column" in error_msg or "1054" in error_msg:
        match = re.search(r"Unknown column '([^']+)'", error_msg)
        if match:
            bad_field = match.group(1).split(".")[-1]  # 去掉表名前缀

            fixed_sql = failed_sql
            if bad_field in _COMMON_FIELD_FIXES:
                fixed_sql = failed_sql.replace(bad_field, _COMMON_FIELD_FIXES[bad_field])
                logger.info(f"[RETRY] 列名修正: {bad_field} → {_COMMON_FIELD_FIXES[bad_field]}")
            else:
                # 尝试加前缀
                for prefix in ["order_", "dim_", "fact_"]:
                    candidate = prefix + bad_field
                    if candidate in failed_sql:
                        continue
                    fixed_sql = failed_sql.replace(bad_field, candidate)
                    logger.info(f"[RETRY] 加前缀尝试: {bad_field} → {candidate}")
                    break

            if fixed_sql != failed_sql:
                try:
                    result = await dw_session.execute(text(fixed_sql))
                    rows = [dict(row) for row in result.mappings().fetchall()]
                    logger.info(f"[RETRY] 修正后 SQL 执行成功: {len(rows)} 行")
                    return fixed_sql
                except Exception:
                    logger.warning(f"[RETRY] 修正后仍失败")

    # LLM 修正路径：快速路径无效时尝试用 LLM
    if schema_text:
        llm_fixed = await _llm_correct_sql(failed_sql, error_msg, schema_text)
        if llm_fixed:
            try:
                result = await dw_session.execute(text(llm_fixed))
                rows = [dict(row) for row in result.mappings().fetchall()]
                logger.info(f"[LLM-RETRY] 执行成功: {len(rows)} 行")
                return llm_fixed
            except Exception:
                logger.warning("[LLM-RETRY] LLM 修正后仍失败")

    return None


async def execute_sqls(sqls: list[dict], dw_session: AsyncSession, schema_text: str = "") -> dict[str, list[dict]]:
    """逐条执行 SQL，失败时自动修正字段名重试"""
    results = {}
    for sql_def in sqls:
        try:
            rows = []
            result = await dw_session.execute(text(sql_def["sql"]))
            for row in result.mappings().fetchall():
                rows.append(dict(row))
            results[sql_def["id"]] = rows
        except Exception as e:
            err_msg = str(e)
            logger.error(f"SQL 执行失败 [{sql_def['id']}]: {err_msg[:200]}")
            # 尝试自动修正（快速路径 + LLM 路径）
            fixed = await _retry_sql(sql_def["sql"], err_msg, dw_session, schema_text)
            if fixed:
                results[sql_def["id"] + "_fixed"] = fixed
                try:
                    rows = []
                    result = await dw_session.execute(text(fixed))
                    for row in result.mappings().fetchall():
                        rows.append(dict(row))
                    results[sql_def["id"]] = rows
                except Exception as e2:
                    results[sql_def["id"]] = []
                    results[f"{sql_def['id']}_error"] = str(e2)
            else:
                results[sql_def["id"]] = []
                results[f"{sql_def['id']}_error"] = err_msg
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
    from app.agent.llm import get_llm
    from decimal import Decimal

    def _convert(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError

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
            context_parts.append(f"[SQL 结果 - {k}]: {json.dumps(summary, ensure_ascii=False, default=_convert)[:2500]}\n")
    if python_results:
        context_parts.append(f"[Python 处理结果]: {json.dumps(python_results, ensure_ascii=False, default=_convert)[:300]}\n")
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
    resp = await get_llm().ainvoke(prompt)
    return resp.content.strip()
