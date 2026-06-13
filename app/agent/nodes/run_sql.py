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
        logger.info(f"SQL执行结果：{result}")
        writer({"type": "progress", "step": step, "status": "success"})
        writer({"type": "result", "data": result})

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
