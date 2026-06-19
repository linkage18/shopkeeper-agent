"""
记忆检索器 — 多级级联检索
每次查询都从各存储层重新读取，不做内存缓存。
优先级：持久记忆 > 长期记忆(approved) > 短期记忆
"""
from app.memory.short_term import get_recent_context
from app.memory.long_term import get_long_term_context
from app.memory.persistent import get_persistent_context


async def retrieve_all(
    query: str,
    session_id: str = "",
    user_id: str = "",
    db_session=None,
) -> str:
    """
    级联检索所有记忆层，拼装成上下文文本返回。
    每次调用都会从磁盘/数据库重新读取，确保"第一次读取"语义。
    """
    from app.core.log import logger
    parts = []

    # 1. 持久记忆（最高优先级）
    if db_session:
        try:
            persistent_ctx = await get_persistent_context(db_session)
            if persistent_ctx:
                parts.append(f"[系统规则]\n{persistent_ctx}")
        except Exception as e:
            logger.warning(f"持久记忆检索失败: {e}")

    # 2. 长期记忆（共享 + 私有）
    try:
        long_ctx = get_long_term_context(query, user_id)
        if long_ctx:
            parts.append(f"[知识定义]\n{long_ctx}")
    except Exception as e:
        logger.warning(f"长期记忆检索失败: {e}")

    # 3. 短期记忆（最近对话上下文）
    if session_id:
        try:
            short_ctx = get_recent_context(session_id, query)
            if short_ctx:
                parts.append(f"[对话历史]\n{short_ctx}")
        except Exception as e:
            logger.warning(f"短期记忆检索失败: {e}")

    return "\n\n".join(parts)
