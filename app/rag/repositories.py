"""
RAG 存储层

DocSubChunkQdrantRepository — 子块向量存储与检索
DocESRepository — 子块全文索引与 BM25 检索

两者独立编写，不继承已有 Repository，不动已有代码。
"""
from dataclasses import asdict

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from elasticsearch import AsyncElasticsearch

from app.conf.app_config import app_config
from app.rag.entities import DocParentChunk, DocSubChunk


class DocSubChunkQdrantRepository:
    """文档子块向量仓储：管理 doc_sub_chunks 集合的写入和检索"""

    def __init__(self, client: AsyncQdrantClient):
        self.client = client
        self.sub_collection = app_config.rag.qdrant.sub_collection
        self.parent_collection = app_config.rag.qdrant.parent_collection

    async def ensure_sub_collection(self):
        """确保子块向量集合存在"""
        if not await self.client.collection_exists(self.sub_collection):
            await self.client.create_collection(
                collection_name=self.sub_collection,
                vectors_config=VectorParams(
                    size=app_config.qdrant.embedding_size,
                    distance=Distance.COSINE,
                ),
            )

    async def ensure_parent_collection(self):
        """确保父块向量集合存在（父块只存 payload，用 placeholder 向量）"""
        if not await self.client.collection_exists(self.parent_collection):
            await self.client.create_collection(
                collection_name=self.parent_collection,
                vectors_config=VectorParams(
                    size=app_config.qdrant.embedding_size,
                    distance=Distance.COSINE,
                ),
            )

    async def upsert_parents(self, parents: list[DocParentChunk], batch_size: int = 10):
        """批量写入父块（向量为全零占位，只存 payload）"""
        import uuid
        points = [
            PointStruct(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, p.id),
                vector=[0.0] * app_config.qdrant.embedding_size,
                payload=asdict(p),
            )
            for p in parents
        ]
        for i in range(0, len(points), batch_size):
            await self.client.upsert(
                collection_name=self.parent_collection,
                points=points[i : i + batch_size],
            )

    async def upsert_sub_chunks(
        self, chunks: list[DocSubChunk], embeddings: list[list[float]], batch_size: int = 10
    ):
        """批量写入子块向量"""
        import uuid
        points = [
            PointStruct(id=uuid.uuid5(uuid.NAMESPACE_DNS, c.id), vector=emb, payload=asdict(c))
            for c, emb in zip(chunks, embeddings)
        ]
        for i in range(0, len(points), batch_size):
            await self.client.upsert(
                collection_name=self.sub_collection,
                points=points[i : i + batch_size],
            )

    async def search_sub_chunks(
        self, embedding: list[float], score_threshold: float = 0.6, limit: int = 20
    ) -> list[tuple[DocSubChunk, float]]:
        """按向量相似度检索子块"""
        result = await self.client.query_points(
            collection_name=self.sub_collection,
            query=embedding,
            limit=limit,
            score_threshold=score_threshold,
        )
        return [(DocSubChunk(**p.payload), p.score) for p in result.points]

    async def get_parent_by_id(self, parent_id: str) -> DocParentChunk | None:
        """按 ID 获取父块"""
        import uuid
        try:
            result = await self.client.retrieve(
                collection_name=self.parent_collection,
                ids=[uuid.uuid5(uuid.NAMESPACE_DNS, parent_id)],
            )
            if result:
                return DocParentChunk(**result[0].payload)
        except Exception as e:
            from app.core.log import logger
            logger.warning(f"Failed to get parent by id: {e}")
            return None
        return None

    async def get_parents_batch(self, parent_ids: list[str]) -> dict[str, DocParentChunk]:
        """批量获取父块"""
        import uuid
        uuids = [uuid.uuid5(uuid.NAMESPACE_DNS, pid) for pid in parent_ids]
        result = await self.client.retrieve(
            collection_name=self.parent_collection,
            ids=uuids,
        )
        return {p.payload["id"]: DocParentChunk(**p.payload) for p in result}


class DocESRepository:
    """文档子块全文检索仓储"""

    def __init__(self, client: AsyncElasticsearch):
        self.client = client
        self.index_name = app_config.rag.es.doc_index_name
        self.index_mappings = {
            "dynamic": False,
            "properties": {
                "id": {"type": "keyword"},
                "parent_id": {"type": "keyword"},
                "file_name": {"type": "text", "analyzer": "ik_max_word"},
                "page_number": {"type": "integer"},
                "content": {"type": "text", "analyzer": "ik_max_word"},
                "title_path": {"type": "text", "analyzer": "ik_smart"},
            },
        }

    async def ensure_index(self):
        """确保索引存在"""
        if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(
                index=self.index_name, mappings=self.index_mappings
            )

    async def index_sub_chunks(self, chunks: list[DocSubChunk], batch_size: int = 20):
        """批量写入子块到全文索引"""
        if not chunks:
            return
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            operations = []
            for chunk in batch:
                operations.append(
                    {"index": {"_index": self.index_name, "_id": chunk.id}}
                )
                operations.append(asdict(chunk))
            await self.client.bulk(operations=operations)

    async def search(
        self, keyword: str, score_threshold: float = 0.6, limit: int = 20
    ) -> list[tuple[DocSubChunk, float]]:
        """按关键词 BM25 全文检索子块"""
        resp = await self.client.search(
            index=self.index_name,
            query={"multi_match": {"query": keyword, "fields": ["content", "file_name", "title_path"]}},
            size=limit,
            min_score=score_threshold,
        )
        results = []
        for hit in resp["hits"]["hits"]:
            chunk = DocSubChunk(**hit["_source"])
            results.append((chunk, hit["_score"]))
        return results
