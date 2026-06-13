"""
文档入库脚本入口

用法: python -m app.scripts_rag.ingest_docs --dir data/docs
      python -m app.scripts_rag.ingest_docs --file README.md
"""
import argparse
import asyncio
from pathlib import Path

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.core.log import logger
from app.rag.repositories import DocESRepository, DocSubChunkQdrantRepository
from app.rag.services import DocIngestionService


async def ingest(path: Path):
    """初始化依赖并执行文档入库"""

    # 初始化客户端
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()

    try:
        # 创建仓储
        doc_qdrant_repo = DocSubChunkQdrantRepository(qdrant_client_manager.client)
        doc_es_repo = DocESRepository(es_client_manager.client)

        # 创建服务
        service = DocIngestionService(
            doc_qdrant_repository=doc_qdrant_repo,
            doc_es_repository=doc_es_repo,
            embedding_client=embedding_client_manager.client,
        )

        # 确保集合和索引存在
        await service.ensure_collections()

        # 收集文件
        if path.is_file():
            files = [path]
        else:
            files = list(path.glob("*.*"))

        # 过滤支持的格式
        supported = {".md", ".txt", ".md", ".html"}
        files = [f for f in files if f.suffix.lower() in supported]

        if not files:
            logger.warning(f"在 {path} 中未找到支持的文档（支持格式: {supported}）")
            return

        logger.info(f"找到 {len(files)} 个文档，开始入库...")

        for file_path in files:
            try:
                result = await service.ingest_file(file_path)
                print(f"  [OK] {result['file_name']}: {result['sub_chunk_count']} 子块")
            except Exception as e:
                print(f"  [FAIL] {file_path.name}: {e}")

        logger.info("入库完成")

    finally:
        # 关闭客户端
        await qdrant_client_manager.close()
        await es_client_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="文档入库：解析 → 切片 → 向量化 → 写入 Qdrant + ES")
    parser.add_argument("--dir", type=str, help="文档目录路径")
    parser.add_argument("--file", type=str, help="单个文件路径")
    args = parser.parse_args()

    if args.dir:
        asyncio.run(ingest(Path(args.dir)))
    elif args.file:
        asyncio.run(ingest(Path(args.file)))
    else:
        print("请指定 --dir 或 --file")
