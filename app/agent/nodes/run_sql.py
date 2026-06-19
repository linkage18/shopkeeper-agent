"""
SQL 执行节点

负责执行最终 SQL，并记录查询结果。
它是当前 SQL 闭环的结束节点，执行完成后流程进入 END。

安全性：执行前通过 sqlglot AST 审查，只放行纯 SELECT。
"""
import sqlglot
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _looks_like_date_field(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in ["date", "time", "day", "month", "year", "dt"])


def _build_chart_data(rows: list[dict], query: str = "") -> dict | None:
    """基于 SQL 结果自动生成前端 ECharts 可消费的数据。"""
    if not rows or not isinstance(rows[0], dict):
        return None

    columns = list(rows[0].keys())
    numeric_columns = [
        col for col in columns
        if any(_is_number(row.get(col)) for row in rows)
    ]
    dimension_columns = [col for col in columns if col not in numeric_columns]

    # 单值结果不强行画图，直接展示表格/指标即可。
    if len(rows) == 1 and len(columns) <= 2:
        return None

    if not numeric_columns:
        return None

    x_field = dimension_columns[0] if dimension_columns else columns[0]
    y_fields = numeric_columns[:3]
    limited_rows = rows[:20]
    labels = [str(row.get(x_field, "")) for row in limited_rows]

    if len(y_fields) == 1:
        y_field = y_fields[0]
        values = [float(row.get(y_field) or 0) for row in limited_rows]
        chart_type = "line" if _looks_like_date_field(x_field) else "bar"
        if len(limited_rows) <= 8 and any(word in query for word in ["占比", "比例", "份额", "分布"]):
            chart_type = "pie"
        return {
            "chart_type": chart_type,
            "title": f"{x_field} - {y_field}",
            "labels": labels,
            "values": values,
            "x_field": x_field,
            "y_fields": [y_field],
        }

    return {
        "chart_type": "bar",
        "title": f"{x_field} 多指标对比",
        "labels": labels,
        "series": [
            {
                "name": y_field,
                "data": [float(row.get(y_field) or 0) for row in limited_rows],
            }
            for y_field in y_fields
        ],
        "x_field": x_field,
        "y_fields": y_fields,
    }


def _assert_readonly_sql(sql: str):
    """
    用 sqlglot 解析 SQL AST，确保只有 SELECT 语句。
    覆盖的绕过方式：
      - UPDATE / DELETE / INSERT / DROP 等 → 类型检查拦截
      - SELECT INTO OUTFILE → Into 节点检查拦截
      - 多层嵌套 UNION 含写操作 → 逐语句检查拦截
      - CTE (WITH ... UPDATE) → 顶层非 SELECT 拦截
    
    抛出 PermissionError 则阻断执行。
    """
    try:
        statements = sqlglot.parse(sql)
    except Exception as e:
        raise PermissionError(f"SQL 解析失败，无法确认安全性: {e}")

    for i, stmt in enumerate(statements):
        if stmt is None:
            continue
        # 只允许 sqlglot.exp.Select 类型
        if not isinstance(stmt, sqlglot.exp.Select):
            raise PermissionError(
                f"阻断非查询语句 (第 {i+1} 条): {type(stmt).__name__}"
            )
        # 即使是 SELECT，也不能有 INTO OUTFILE 等写文件操作
        if stmt.find(sqlglot.exp.Into):
            raise PermissionError("阻断 SELECT INTO（写文件操作）")


async def run_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """执行 SQL 并产出最终问数结果"""

    writer = runtime.stream_writer
    step = "执行SQL"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # 重试用尽后的友好提示
        fatal_error = state.get("fatal_error", "")
        if fatal_error:
            logger.warning(f"[SQL] {fatal_error}")
            writer({"type": "progress", "step": step, "status": "success"})
            writer({"type": "result", "data": {
                "error": "无法生成正确的 SQL 查询语句，请尝试换一种描述方式。",
                "detail": fatal_error[:200],
            }})
            return

        sql = state["sql"]
        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        # sqlglot AST 审查：只放行纯 SELECT
        try:
            _assert_readonly_sql(sql)
        except PermissionError as e:
            logger.warning(f"[SECURITY] {e}: {sql[:100]}")
            writer({"type": "progress", "step": step, "status": "success"})
            writer({"type": "result", "data": {"error": f"已自动阻断: {e}"}})
            return

        # 真实数据库访问统一封装在仓储层，节点只负责从状态取 SQL 并触发执行
        result = await dw_mysql_repository.run(sql)
        chart_data = _build_chart_data(result, state.get("query", ""))
        payload = {
            "sql": sql,
            "rows": result,
            "row_count": len(result),
            "chart_data": chart_data,
        }
        logger.info(f"SQL执行结果：{result}")
        writer({"type": "progress", "step": step, "status": "success"})
        writer({"type": "result", "data": payload})

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
