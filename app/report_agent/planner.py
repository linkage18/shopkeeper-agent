"""
Report Planner — LLM 根据用户问题和数据库 Schema 规划 SQL + Python 代码
"""
from app.agent.llm import llm


async def plan_report(query: str, schema_text: str) -> dict:
    """规划报告生成流程：SQL 列表 + Python 预处理 + 图表配置"""
    prompt = (
        "你是一个数据分析专家。根据用户问题和数据库表结构，规划如何生成一份数据分析报告。\n\n"
        f"用户问题：{query}\n\n"
        f"数据库表结构：\n{schema_text}\n\n"
        "请输出 JSON 格式的规划（不要 markdown 代码块）：\n"
        "{\n"
        '  "sqls": [\n'
        '    {"id": "唯一标识", "sql": "完整的 SQL 查询语句"},\n'
        '    ... (可以有多条 SQL)\n'
        "  ],\n"
        '  "python_preprocess": "用 pandas 对 SQL 结果做预处理的 Python 代码。可用变量：各 sql_id 对应的 DataFrame。只允许 pandas/numpy/math。",\n'
        '  "chart_type": "line | bar | pie",\n'
        '  "chart_title": "图表标题",\n'
        '  "report_title": "报告标题"\n'
        "}\n\n"
        "规则：\n"
        "- SQL 只做查询，不修改数据\n"
        "- Python 只允许 pandas 基本操作（merge/groupby/pivot/value_counts/sort_values）\n"
        "- chart_type 根据数据特点选择最合适的图表类型"
    )
    resp = await llm.ainvoke(prompt)
    import json
    text = resp.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())
