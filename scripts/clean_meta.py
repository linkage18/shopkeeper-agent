"""清空 meta 业务表和 Qdrant 集合"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from sqlalchemy import text
from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager


async def clean():
    meta_mysql_client_manager.init()
    qdrant_client_manager.init()

    # 1. 清 MySQL 表
    async with meta_mysql_client_manager.session_factory() as s:
        for tbl in ["column_metric", "column_info", "metric_info", "table_info", "memory_persistent"]:
            await s.execute(text(f"TRUNCATE TABLE {tbl}"))
            print(f"TRUNCATE MySQL {tbl}")
        await s.commit()

    # 2. 清 Qdrant 集合
    c = qdrant_client_manager.client
    for col in ["column_info_collection", "metric_info_collection"]:
        if await c.collection_exists(col):
            await c.delete_collection(col)
            print(f"删除 Qdrant 集合 {col}")

    print("清理完成")


asyncio.run(clean())
