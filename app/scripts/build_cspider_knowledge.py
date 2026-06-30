"""
CSpider 知识库构建脚本

为单个 CSpider 数据库生成 MetaMySQL + Qdrant + ES 知识库索引。
用法:
  python -m app.scripts.build_cspider_knowledge --db-id store_1
  python -m app.scripts.build_cspider_knowledge --db-id academic --clear
"""
import argparse
import asyncio
import sys
from pathlib import Path

import yaml

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.core.log import logger

CSPIDER_YAML_DIR = Path("conf/cspider")


async def build_cspider_knowledge(db_id: str, clear: bool = False):
    """为单个 CSpider 数据库构建完整知识库索引"""

    # ── 1. 读取 YAML 配置 ──
    yaml_path = CSPIDER_YAML_DIR / f"{db_id}.yaml"
    if not yaml_path.exists():
        logger.error(f"CSpider YAML not found: {yaml_path}")
        return False

    with open(yaml_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    tables_cfg = config.get("tables", [])
    metrics_cfg = config.get("metrics", [])
    logger.info(f"Loading {db_id}: {len(tables_cfg)} tables, {len(metrics_cfg)} metrics")

    # ── 2. 初始化客户端 ──
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()

    try:
        async with meta_mysql_client_manager.session_factory() as meta_session:
            meta_repo = MetaMySQLRepository(meta_session)
            col_qdrant = ColumnQdrantRepository(qdrant_client_manager.client)
            metric_qdrant = MetricQdrantRepository(qdrant_client_manager.client)
            value_es = ValueESRepository(es_client_manager.client)
            embedder = embedding_client_manager.client

            # ── 3. 构建表 + 字段信息 ──
            table_infos: list[TableInfo] = []
            column_infos: list[ColumnInfo] = []

            for tbl in tables_cfg:
                table_id = f"{db_id}.{tbl['name']}"
                table_info = TableInfo(
                    id=table_id,
                    name=tbl["name"],
                    role=tbl.get("role", "dim"),
                    description=tbl.get("description", ""),
                )
                table_infos.append(table_info)

                for col in tbl.get("columns", []):
                    col_name = col["name"]
                    col_id = f"{table_id}.{col_name}"
                    column_info = ColumnInfo(
                        id=col_id,
                        name=col_name,
                        type=col.get("type", "VARCHAR(255)"),
                        role=col.get("role", "dimension"),
                        examples=[],
                        description=col.get("description", ""),
                        alias=col.get("alias", []),
                        table_id=table_id,
                    )
                    column_infos.append(column_info)

            # 先清空已有数据
            if clear:
                logger.info(f"Clearing existing metadata for {db_id}...")
                # MetaMySQL: find and remove existing entries
                for col in column_infos:
                    existing = await meta_repo.get_column_info_by_id(col.id)
                    if existing:
                        async with meta_session.begin():
                            from app.models.column_info import ColumnInfoMySQL
                            obj = await meta_session.get(ColumnInfoMySQL, col.id)
                            if obj:
                                await meta_session.delete(obj)
                for tbl in table_infos:
                    existing = await meta_repo.get_table_info_by_id(tbl.id)
                    if existing:
                        async with meta_session.begin():
                            from app.models.table_info import TableInfoMySQL
                            obj = await meta_session.get(TableInfoMySQL, tbl.id)
                            if obj:
                                await meta_session.delete(obj)

            # 保存表 + 字段到 MetaMySQL
            async with meta_session.begin():
                meta_repo.save_table_infos(table_infos)
                meta_repo.save_column_infos(column_infos)
            logger.info(f"Saved {len(table_infos)} tables and {len(column_infos)} columns to MetaMySQL")

            # ── 4. 字段 → Qdrant 向量索引 ──
            await col_qdrant.ensure_collection()
            points = []
            for col in column_infos:
                texts = [col.name, col.description] + col.alias
                for text in texts:
                    if text and text.strip():
                        points.append({"text": text, "payload": col.__dict__.copy()})

            if points:
                embeddings = []
                batch_size = 20
                for i in range(0, len(points), batch_size):
                    batch = [p["text"] for p in points[i:i + batch_size]]
                    batch = [t if t and t.strip() else "empty" for t in batch]
                    emb = await embedder.aembed_documents(batch)
                    embeddings.extend(emb)

                ids = [str(hash(p["text"] + p["payload"]["id"])) for p in points]
                payloads = [p["payload"] for p in points]
                await col_qdrant.upsert(ids, embeddings, payloads)
                logger.info(f"Indexed {len(points)} column vectors to Qdrant")

            # ── 5. 指标 → MetaMySQL + Qdrant ──
            if metrics_cfg:
                metric_infos: list[MetricInfo] = []
                column_metrics: list[ColumnMetric] = []
                for m in metrics_cfg:
                    metric_info = MetricInfo(
                        id=f"{db_id}.{m['name']}",
                        name=m["name"],
                        description=m.get("description", ""),
                        relevant_columns=m.get("relevant_columns", []),
                        alias=m.get("alias", []),
                    )
                    metric_infos.append(metric_info)
                    for col in metric_info.relevant_columns:
                        column_metrics.append(
                            ColumnMetric(column_id=f"{db_id}.{col}", metric_id=metric_info.id)
                        )

                async with meta_session.begin():
                    meta_repo.save_metric_infos(metric_infos)
                    meta_repo.save_column_metrics(column_metrics)
                logger.info(f"Saved {len(metric_infos)} metrics to MetaMySQL")

                # 指标 → Qdrant
                await metric_qdrant.ensure_collection()
                mpoints = []
                for m in metric_infos:
                    texts = [m.name, m.description] + m.alias
                    for text in texts:
                        if text and text.strip():
                            mpoints.append({"text": text, "payload": m.__dict__.copy()})

                if mpoints:
                    membs = []
                    for i in range(0, len(mpoints), batch_size):
                        batch = [p["text"] for p in mpoints[i:i + batch_size]]
                        batch = [t if t and t.strip() else "empty" for t in batch]
                        emb = await embedder.aembed_documents(batch)
                        membs.extend(emb)
                    mids = [str(hash(p["text"] + p["payload"]["id"])) for p in mpoints]
                    mpays = [p["payload"] for p in mpoints]
                    await metric_qdrant.upsert(mids, membs, mpays)
                    logger.info(f"Indexed {len(mpoints)} metric vectors to Qdrant")

            logger.info(f"CSpider knowledge build complete for '{db_id}'")
            return True

    finally:
        await meta_mysql_client_manager.close()
        await dw_mysql_client_manager.close()
        await qdrant_client_manager.close()
        await es_client_manager.close()


def main():
    parser = argparse.ArgumentParser(description="CSpider 知识库构建工具")
    parser.add_argument("--db-id", required=True, help="CSpider database ID")
    parser.add_argument("--clear", action="store_true", help="清空已有数据后重新构建")
    args = parser.parse_args()

    success = asyncio.run(build_cspider_knowledge(args.db_id, args.clear))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
