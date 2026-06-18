"""
Schema Analyzer — 读取数据库表结构，分析维度/指标/关系
"""
from __future__ import annotations
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_schema(session: AsyncSession) -> dict[str, Any]:
    """读取 dw 库的表结构，返回维度、指标、关系"""
    # 读取所有表名
    tables_result = await session.execute(
        text("SELECT TABLE_NAME, TABLE_COMMENT FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dw'")
    )
    tables_info = []
    for row in tables_result.mappings().fetchall():
        table_name = row["TABLE_NAME"]
        # 读取字段
        cols_result = await session.execute(
            text(f"SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT, COLUMN_KEY FROM INFORMATION_SCHEMA.COLUMNS "
                 f"WHERE TABLE_SCHEMA = 'dw' AND TABLE_NAME = '{table_name}'")
        )
        columns = []
        for col in cols_result.mappings().fetchall():
            col_type = col["COLUMN_TYPE"]
            col_name = col["COLUMN_NAME"]
            # 判断角色
            if col["COLUMN_KEY"] == "PRI":
                role = "primary_key"
            elif col_name.endswith("_id") and col_name != col_name.removesuffix("_id") + "_id":
                role = "foreign_key"
            elif any(t in col_type for t in ["float", "double", "decimal", "int", "bigint"]):
                role = "measure"
            else:
                role = "dimension"
            columns.append({
                "name": col_name,
                "type": col_type,
                "comment": col["COLUMN_COMMENT"] or "",
                "role": role,
            })
        # 判断表角色
        table_role = "fact" if table_name.startswith("fact_") else "dim" if table_name.startswith("dim_") else "unknown"
        tables_info.append({
            "name": table_name,
            "comment": row["TABLE_COMMENT"] or "",
            "role": table_role,
            "columns": columns,
        })

    # 分析可用的维度字段和指标字段
    dimensions = []
    measures = []
    for table in tables_info:
        for col in table["columns"]:
            entry = {
                "table": table["name"],
                "table_comment": table["comment"],
                "column": col["name"],
                "comment": col["comment"],
                "type": col["type"],
                "role": col["role"],
            }
            if col["role"] == "measure":
                measures.append(entry)
            elif col["role"] == "dimension":
                dimensions.append(entry)

    return {
        "tables": tables_info,
        "dimensions": dimensions,
        "measures": measures,
    }
