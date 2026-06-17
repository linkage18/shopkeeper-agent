from app.knowledge.manager import search_knowledge, get_knowledge


async def knowledge_augmented_query(query: str, user_id: str = "") -> str:
    results = search_knowledge(query, user_id)
    if not results:
        return ""

    context_parts = []
    for r in results[:5]:
        entry = get_knowledge(r["title"], user_id)
        if entry:
            context_parts.append(
                f"【{entry.title}】\n定义：{entry.definition}\n"
                f"涉及表：{', '.join(entry.tables)}\n"
                f"示例SQL：{entry.example_sql}"
            )
    return "\n\n".join(context_parts)
