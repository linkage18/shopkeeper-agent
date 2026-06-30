"""
SQL 生成节点

负责根据用户问题和前面整理出的表结构 指标 日期 数据库环境生成候选 SQL。
本节点只生成 SQL，不做校验和执行，后续会交给 validate_sql 和 run_sql 继续处理。
"""

import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import get_llm
from app.agent.nodes.run_sql import _has_chart_keyword
from app.agent.state import DataAgentState
from app.conf.app_config import app_config
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """基于已检索和过滤的上下文生成 SQL"""

    writer = runtime.stream_writer
    step = "生成SQL"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # 这些上下文都由前置节点准备完成，模型只在给定表 字段 指标口径范围内生成 SQL
        table_infos = state["table_infos"]
        metric_infos = state["metric_infos"]
        date_info = state["date_info"]
        db_info = state["db_info"]
        query = state["query"]
        memory_context = state.get("memory_context", "")

        # 检测用户是否要求图表/可视化，在 prompt 中注入提示
        # 从配置读取图表关键词（允许用户自定义）
        chart_hint = (
            "\n【提示】用户希望看到可视化图表。请确保 SQL 返回多行数据（维度 + 数值），"
            "不要只返回一个汇总值。例如：GROUP BY 地区/品类/品牌 等维度。"
            if _has_chart_keyword(query) else ""
        )

        # 如果有记忆上下文，注入到 prompt 顶部
        template = load_prompt("generate_sql")
        if memory_context.strip():
            template = f"\n\n【知识参考】\n{memory_context}" + "\n\n" + template
        prompt = PromptTemplate(
            template=template + chart_hint,
            input_variables=[
                "table_infos",
                "metric_infos",
                "date_info",
                "db_info",
                "query",
            ],
        )
        # SQL 生成节点只需要纯文本 SQL，不能要求模型输出 JSON 或 Markdown 代码块
        output_parser = StrOutputParser()
        chain = prompt | get_llm() | output_parser

        result = await chain.ainvoke(
            {
                # YAML 更适合放进提示词：保留嵌套结构 顺序和中文说明，方便模型理解表字段关系
                "table_infos": yaml.dump(
                    table_infos, allow_unicode=True, sort_keys=False
                ),
                "metric_infos": yaml.dump(
                    metric_infos, allow_unicode=True, sort_keys=False
                ),
                "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
                "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
                "query": query,
            }
        )

        # 如果 LLM 返回空 SQL，重试一次
        if not result or not result.strip():
            logger.warning("生成SQL为空，重试一次...")
            writer({"type": "progress", "step": step, "status": "running"})
            # 在chart_hint前插入：强制要求生成非空SQL
            force_template = template + "\n注意：必须生成一条完整的 SQL 语句，不得为空！\n" + chart_hint
            force_prompt = PromptTemplate(
                template=force_template,
                input_variables=["table_infos", "metric_infos", "date_info", "db_info", "query"],
            )
            chain2 = force_prompt | get_llm() | output_parser
            result = await chain2.ainvoke({
                "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
                "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False),
                "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
                "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
                "query": query,
            })

        logger.info(f"生成的SQL：{result}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"sql": result}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise


