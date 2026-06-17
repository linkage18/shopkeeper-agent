from datetime import datetime

from app.agent.llm import llm
from app.conf.app_config import app_config
from app.knowledge.manager import save_knowledge
from app.knowledge.models import KnowledgeEntry


async def extract_knowledge(query: str, sql: str, result: str, user_id: str):
    prompt = (
        f"判断以下对话中是否包含有价值的业务知识定义。\n\n"
        f"用户问题：{query}\n"
        f"生成的SQL：{sql}\n"
        f"查询结果：{str(result)[:200]}\n\n"
        f"如果有业务口径、指标定义、规则说明等，以JSON格式输出。"
        f"格式：{{\"has_knowledge\": true/false, \"title\": \"知识标题\", \"definition\": \"定义内容\", "
        f"\"tables\": [\"涉及的表\"], \"example_sql\": \"\", \"tags\": [\"标签\"]}}\n"
        f"如果没有，返回 {{\"has_knowledge\": false}}"
    )
    try:
        resp = await llm.ainvoke(prompt)
        import json
        data = json.loads(resp.content.strip().strip("```json").strip("```").strip())
        if data.get("has_knowledge"):
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = KnowledgeEntry(
                title=data["title"],
                definition=data["definition"],
                tables=data.get("tables", []),
                example_sql=data.get("example_sql", sql),
                tags=data.get("tags", []),
                created_by=user_id,
                created_at=now,
                status="pending",
            )
            save_knowledge(entry, user_id, is_shared=True)
    except Exception:
        pass
