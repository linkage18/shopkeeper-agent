"""
ReportPipeline — 报告生成管线，以注入方式管理各步骤依赖
"""
import json
import time
from datetime import date
from decimal import Decimal
from typing import Any, AsyncIterator

from app.report_agent.planner import plan_report
from app.report_agent.executor import execute_sqls, execute_python, generate_report_text
from app.report_agent.renderer import build_chart_data
from app.schema_analyzer.analyzer import get_schema as get_db_schema
from app.core.log import logger


def _default_json(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=_default_json)}\n\n"


class ReportPipeline:
    """报告生成管线，所有依赖通过 constructor 注入"""

    def __init__(self, dw_manager, meta_manager):
        self._dw = dw_manager
        self._meta = meta_manager

    async def run(self, query: str) -> AsyncIterator[str]:
        """执行报告管线，逐个 yield SSE 事件字符串"""
        try:
            # ── 1. 读取 Schema ──
            yield _sse({"type": "progress", "step": "读取 Schema", "status": "running"})
            t0 = time.perf_counter()
            async with self._dw.session_factory() as session:
                schema = await get_db_schema(session)
                field_index_parts = ["可用字段列表："]
                for t in schema.get("tables", []):
                    field_index_parts.append(f"\n表 {t['name']} ({t['role']}):")
                    for c in t["columns"]:
                        desc = f" ({c['comment']})" if c["comment"] else ""
                        field_index_parts.append(f"  - {c['name']}  [{c['type']}]  {c['role']}{desc}")
                field_index = "\n".join(field_index_parts)
                schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
                if len(schema_text) > 6000:
                    schema_text = schema_text[:3000] + "\n...\n" + field_index[:3000]
            yield _sse({"type": "progress", "step": "读取 Schema", "status": "success", "duration_ms": int((time.perf_counter() - t0) * 1000)})

            # ── 1.5 记忆检索 ──
            memory_ctx = ""
            try:
                from app.memory.retriever import retrieve_all
                async with self._meta.session_factory() as msession:
                    memory_ctx = await retrieve_all(query=query, db_session=msession)
            except Exception as e:
                logger.warning(f"报告记忆检索失败: {e}")

            # ── 2. 规划 ──
            yield _sse({"type": "progress", "step": "规划报告", "status": "running"})
            t0 = time.perf_counter()
            plan = await plan_report(query, schema_text, current_date=date.today().strftime("%Y-%m-%d"), memory_context=memory_ctx)
            sqls = plan.get("sqls", [])
            python_code = plan.get("python_preprocess", "")

            chart_list = plan.get("charts", None)
            if chart_list:
                chart_info_list = chart_list
            elif plan.get("chart_type"):
                chart_info_list = [{
                    "sql_id": sqls[0]["id"] if sqls else "",
                    "chart_type": plan.get("chart_type", "bar"),
                    "chart_title": plan.get("chart_title", "分析图表"),
                }]
            else:
                chart_info_list = []
            chart_info_map = {c["sql_id"]: c for c in chart_info_list if c.get("sql_id")}
            yield _sse({"type": "progress", "step": "规划报告", "status": "success", "detail": plan, "duration_ms": int((time.perf_counter() - t0) * 1000)})

            # ── 3. 执行 SQL ──
            yield _sse({"type": "progress", "step": "执行 SQL", "status": "running"})
            t0 = time.perf_counter()
            async with self._dw.session_factory() as session:
                sql_results = await execute_sqls(sqls, session, schema_text=schema_text)
            for sql_id, data in sql_results.items():
                if sql_id.endswith("_error"):
                    yield _sse({"type": "result", "sql_id": sql_id, "error": data})
                else:
                    yield _sse({"type": "result", "sql_id": sql_id, "data": data[:50]})
            yield _sse({"type": "progress", "step": "执行 SQL", "status": "success", "duration_ms": int((time.perf_counter() - t0) * 1000)})

            # ── 3.5 空结果检查 ──
            all_empty = True
            for sql_def in sqls:
                data = sql_results.get(sql_def["id"], [])
                if data:
                    all_empty = False
                    break
            if all_empty:
                errors = [v for k, v in sql_results.items() if k.endswith("_error")]
                error_info = errors[0] if errors else ""
                yield _sse({"type": "ask_user",
                    "message": "查询未返回任何数据。系统不确定原因，需要你确认：",
                    "suggestions": [
                        "数据表中可能还没有对应年份的记录，请确认年份是否正确",
                        "字段名可能不匹配，请确认表结构中的字段名",
                        "时间范围或过滤条件可能过于严格",
                    ],
                    "detail": error_info[:500] if error_info else "",
                })
                return

            # ── 4. Python 预处理 ──
            yield _sse({"type": "progress", "step": "数据处理", "status": "running"})
            t0 = time.perf_counter()
            if python_code:
                python_results = await execute_python(python_code, sql_results)
            else:
                python_results = {}
            yield _sse({"type": "progress", "step": "数据处理", "status": "success", "python_results": python_results, "duration_ms": int((time.perf_counter() - t0) * 1000)})

            # ── 5. 图表 ──
            yield _sse({"type": "progress", "step": "构建图表", "status": "running"})
            t0 = time.perf_counter()
            charts = []
            for sql_def in sqls:
                data = sql_results.get(sql_def["id"], [])
                if not data:
                    continue
                cfg = chart_info_map.get(sql_def["id"], {})
                cfg["chart_id"] = sql_def["id"]
                cfg["chart_name"] = cfg.get("chart_title", sql_def["id"])
                cd = build_chart_data(data, cfg)
                if cd:
                    charts.append(cd)
                    yield _sse({"type": "chart", "chart_id": sql_def["id"], "chart_data": cd})
            if charts:
                yield _sse({"type": "result", "chart_data": charts[0]})
            yield _sse({"type": "progress", "step": "构建图表", "status": "success", "duration_ms": int((time.perf_counter() - t0) * 1000)})

            # ── 6. 报告文本 ──
            yield _sse({"type": "progress", "step": "生成报告", "status": "running"})
            t0 = time.perf_counter()
            report_text = await generate_report_text(query, sql_results, python_results or {}, chart_info_list[0] if chart_info_list else {})
            yield _sse({"type": "result", "report_md": report_text})
            yield _sse({"type": "progress", "step": "生成报告", "status": "success", "duration_ms": int((time.perf_counter() - t0) * 1000)})

            yield _sse({"type": "progress", "step": "完成", "status": "success"})

        except Exception as e:
            logger.error(f"Report 生成失败: {e}")
            yield _sse({"type": "error", "message": f"报告生成失败: {str(e)}"})
