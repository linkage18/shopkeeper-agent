from datetime import datetime

from app.agent.llm import llm
from app.knowledge.manager import save_knowledge
from app.knowledge.models import KnowledgeEntry


async def extract_knowledge_from_report(params: dict, results: dict[str, list[dict]], user_id: str):
    metric = params.get("metric", "")
    dimension = params.get("dimension", "")
    if not metric and not dimension:
        return
    text = f"分析发现：{metric} 按 {dimension} 分布"
    prompt = (
        f"以下是一次数据分析的结果摘要。判断是否包含有价值的业务知识定义（如指标口径、规则说明）。\n\n"
        f"分析参数：{str(params)[:200]}\n"
        f"结果摘要：{text}\n\n"
        f"如果有，输出JSON：{{\"has_knowledge\": true, \"title\": \"...\", \"definition\": \"...\", \"tags\": [...]}}\n"
        f"如果没有，输出 {{\"has_knowledge\": false}}"
    )
    try:
        import json
        resp = await llm.ainvoke(prompt)
        data = json.loads(resp.content.strip().strip("```json").strip("```").strip())
        if data.get("has_knowledge"):
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = KnowledgeEntry(
                title=data["title"], definition=data["definition"],
                tags=data.get("tags", []), created_by=user_id,
                created_at=now, status="pending",
            )
            save_knowledge(entry, user_id, is_shared=True)
    except Exception:
        pass
