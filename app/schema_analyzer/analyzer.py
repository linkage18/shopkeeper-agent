"""
Schema Analyzer — 读取数据库表结构，分析维度/指标/关系
优化：单次 COLUMNS 查询 + 60s 内存缓存
"""
from __future__ import annotations
import asyncio
import time
from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.conf.app_config import app_config

_schema_cache: dict[str, Any] = {}
_schema_cache_time: float = 0
_schema_lock = asyncio.Lock()
CACHE_TTL = 600


def clear_schema_cache():
    """手动清理 Schema 缓存，适合表结构变更后刷新。"""
    global _schema_cache, _schema_cache_time
    _schema_cache = {}
    _schema_cache_time = 0


async def get_schema(session: AsyncSession, *, refresh: bool = False) -> dict[str, Any]:
    """读取 dw 库的表结构，返回维度、指标、关系（带缓存）"""
    global _schema_cache, _schema_cache_time
    now = time.time()
    if not refresh and _schema_cache and now - _schema_cache_time < CACHE_TTL:
        return _schema_cache

    async with _schema_lock:
        now = time.time()
        if not refresh and _schema_cache and now - _schema_cache_time < CACHE_TTL:
            return _schema_cache

        schema_name = app_config.db_dw.database
        cols_result = await session.execute(
            text(
                """
                SELECT c.TABLE_NAME, c.COLUMN_NAME, c.COLUMN_TYPE,
                       c.COLUMN_COMMENT, c.COLUMN_KEY, t.TABLE_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS c
                LEFT JOIN INFORMATION_SCHEMA.TABLES t
                  ON t.TABLE_SCHEMA = c.TABLE_SCHEMA
                 AND t.TABLE_NAME = c.TABLE_NAME
                WHERE c.TABLE_SCHEMA = :schema_name
                ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
                """
            ),
            {"schema_name": schema_name},
        )

        table_columns: dict[str, list[dict]] = defaultdict(list)
        for row in cols_result.mappings().fetchall():
            table_columns[row["TABLE_NAME"]].append(dict(row))

        tables_info = []
        all_dimensions = []
        all_measures = []

        for table_name, columns in table_columns.items():
            table_role = (
                "fact"
                if table_name.startswith("fact_")
                else "dim"
                if table_name.startswith("dim_")
                else "unknown"
            )
            table_comment = columns[0].get("TABLE_COMMENT") or ""
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
                flat = {
                    "table": table_name,
                    "table_comment": table_comment,
                    "column": col_name,
                    "comment": col["COLUMN_COMMENT"] or "",
                    "type": col_type,
                    "role": role,
                }
                if role == "measure":
                    all_measures.append(flat)
                elif role == "dimension":
                    all_dimensions.append(flat)

            tables_info.append(
                {
                    "name": table_name,
                    "comment": table_comment,
                    "role": table_role,
                    "columns": cols,
                }
            )

        result = {
            "tables": tables_info,
            "dimensions": all_dimensions,
            "measures": all_measures,
        }

        _schema_cache = result
        _schema_cache_time = time.time()
        return result
