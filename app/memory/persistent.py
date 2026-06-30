"""
持久记忆 — 系统级规则与安全策略
存储在 MySQL meta 库，仅管理员可修改。
每次读取都从数据库查询，不做缓存。
"""
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

PERSISTENT_TABLE = "memory_persistent"


async def ensure_table(session: AsyncSession):
    """确保持久记忆表存在"""
    sql = f"""
    CREATE TABLE IF NOT EXISTS {PERSISTENT_TABLE} (
        id VARCHAR(64) PRIMARY KEY,
        category VARCHAR(32) NOT NULL,
        name VARCHAR(128) NOT NULL,
        content TEXT NOT NULL,
        priority INT DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """
    await session.execute(text(sql))
    await session.commit()


async def list_persistent(session: AsyncSession) -> list[dict]:
    await ensure_table(session)
    result = await session.execute(
        text(f"SELECT * FROM {PERSISTENT_TABLE} ORDER BY priority DESC, category")
    )
    return [dict(row) for row in result.mappings().fetchall()]


async def save_persistent(session: AsyncSession, entry: dict):
    await ensure_table(session)
    sql = f"""
    INSERT INTO {PERSISTENT_TABLE} (id, category, name, content, priority)
    VALUES (:id, :category, :name, :content, :priority)
    ON DUPLICATE KEY UPDATE category=:category, name=:name, content=:content, priority=:priority
    """
    await session.execute(text(sql), entry)
    await session.commit()


async def delete_persistent(session: AsyncSession, entry_id: str):
    await session.execute(
        text(f"DELETE FROM {PERSISTENT_TABLE} WHERE id = :id"), {"id": entry_id}
    )
    await session.commit()


async def get_persistent_context(session: AsyncSession) -> str:
    """获取持久记忆上下文文本，拼入 system prompt"""
    try:
        await ensure_table(session)
        result = await session.execute(
            text(f"SELECT name, content FROM {PERSISTENT_TABLE} WHERE priority >= 0 ORDER BY priority DESC")
        )
        rows = result.mappings().fetchall()
        if not rows:
            return ""
        parts = [f"【{row['name']}】\n{row['content']}" for row in rows]
        return "\n\n".join(parts)
    except Exception as e:
        from app.core.log import logger
        logger.warning(f"Persistent memory load failed: {e}")
        return ""
