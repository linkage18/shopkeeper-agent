"""
RAG Agent 运行上下文

Context 保存一次图执行中不参与状态合并的外部依赖。
节点通过 runtime.context 读取，不需要把连接对象塞进 State。
"""
from typing import TypedDict

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.rag.repositories import DocSubChunkQdrantRepository, DocESRepository


class RagAgentContext(TypedDict):
    """LangGraph Runtime 中传递的上下文对象"""

    # 文档子块向量仓储（Qdrant）
    doc_qdrant_repository: DocSubChunkQdrantRepository
    # 文档全文检索仓储（ES）
    doc_es_repository: DocESRepository
    # Embedding 客户端，负责将关键词转为 query vector
    embedding_client: HuggingFaceEndpointEmbeddings
    # 元数据仓储，用于 MySQL 精确匹配回调
    # v1 用 embedding_client 做 embedding 后走 Qdrant，暂不依赖 MySQL
    meta_mysql_repository: object | None = None
