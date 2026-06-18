"""
Schema Analyzer — 读取数据库表结构，分析维度/指标/关系
优化：单次 COLUMNS 查询 + 60s 内存缓存
"""
from __future__ import annotations
import time
from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_schema_cache: dict[str, Any] = {}
_schema_cache_time: float = 0
CACHE_TTL = 60


async def get_schema(session: AsyncSession) -> dict[str, Any]:
    """读取 dw 库的表结构，返回维度、指标、关系（带缓存）"""
    global _schema_cache, _schema_cache_time
    now = time.time()
    if now - _schema_cache_time < CACHE_TTL:
        return _schema_cache

    # 单次查询所有表的字段信息
    cols_result = await session.execute(text("""
        SELECT c.TABLE_NAME, c.COLUMN_NAME, c.COLUMN_TYPE,
               c.COLUMN_COMMENT, c.COLUMN_KEY
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dw'
        ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
    """))

    # 按表名分组
    table_columns: dict[str, list[dict]] = defaultdict(list)
    for row in cols_result.mappings().fetchall():
        table_columns[row["TABLE_NAME"]].append(dict(row))

    # 构建 tables_info
    tables_info = []
    all_dimensions = []
    all_measures = []

    for table_name, columns in table_columns.items():
        table_role = "fact" if table_name.startswith("fact_") else "dim" if table_name.startswith("dim_") else "unknown"
        cols = []
        for col in columns:
            col_type = col["COLUMN_TYPE"]
            col_name = col["COLUMN_NAME"]
            if col["COLUMN_KEY"] == "PRI":
                role = "primary_key"
            elif col_name.endswith("_id"):
                role = "foreign_key"
            elif any(t in col_type for t in ["float", "double", "decimal", "int", "bigint"]):
                role = "measure"
            else:
                role = "dimension"
            entry = {
                "name": col_name,
                "type": col_type,
                "comment": col["COLUMN_COMMENT"] or "",
                "role": role,
            }
            cols.append(entry)
            # 收集到维度/指标总表
            flat = {"table": table_name, "table_comment": "", "column": col_name, "comment": col["COLUMN_COMMENT"] or "", "type": col_type, "role": role}
            if role == "measure":
                all_measures.append(flat)
            elif role == "dimension":
                all_dimensions.append(flat)

        tables_info.append({
            "name": table_name,
            "comment": "",
            "role": table_role,
            "columns": cols,
        })

    result = {
        "tables": tables_info,
        "dimensions": all_dimensions,
        "measures": all_measures,
    }

    _schema_cache = result
    _schema_cache_time = now
    return result
