"""
数仓 MySQL 仓储

这一层对应文档里的 DW Repository，职责是到真实数仓中补齐配置文件里
没有显式维护的信息，例如字段类型和字段示例值。Service 层只关心
"需要哪些信息"，具体怎样查数仓由仓储层统一封装
SQL 生成闭环中的数据库环境读取 SQL 校验和最终查询执行也集中放在这里
"""

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# 表名白名单：只允许字母、数字、下划线和中文（防止 SQL 注入）
_VALID_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_一-鿿]+$")


def _safe_identifier(name: str) -> str:
    """校验表名/列名是否为合法标识符，防止 SQL 注入"""
    if not _VALID_IDENTIFIER.match(name):
        raise ValueError(f"非法标识符: {name}")
    return name


class DWMySQLRepository:
    """负责查询数仓真实表结构和字段样例值"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_column_types(self, table_name: str) -> dict[str, str]:
        """查询整张表的字段类型，作为 ColumnInfo.type 的真实来源"""
        safe_table = _safe_identifier(table_name)
        sql = f"show columns from `{safe_table}`"
        result = await self.session.execute(text(sql))
        result_dict = result.mappings().fetchall()
        return {row["Field"]: row["Type"] for row in result_dict}

    async def get_column_values(
        self, table_name: str, column_name: str, limit: int = 10
    ) -> list[Any]:
        """抽样查询字段示例值，供元数据入库和后续检索链路复用"""
        safe_table = _safe_identifier(table_name)
        safe_column = _safe_identifier(column_name)
        sql = f"select distinct `{safe_column}` from `{safe_table}` limit :limit"
        result = await self.session.execute(text(sql), {"limit": limit})
        return [row[0] for row in result.fetchall()]

    async def validate(self, sql: str):
        """用 EXPLAIN 让数据库提前解析 SQL，发现语法 表名 字段名等错误"""
        await self.session.execute(text(f"explain {sql}"))

    async def get_db_info(self) -> dict[str, str]:
        """获取数据库方言和版本信息"""
        result = await self.session.execute(text("select version() as ver"))
        ver = result.scalar_one()
        return {"dialect": "mysql", "version": ver}

    async def run(self, sql: str) -> list[dict]:
        """执行 SQL 并返回结果列表"""
        result = await self.session.execute(text(sql))
        columns = result.keys()
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
