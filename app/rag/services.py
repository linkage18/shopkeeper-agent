"""
RAG 服务层

DocIngestionService — 文档入库：解析 → 切片 → 向量化 → 写入
RagQueryService — RAG 问答：组装 state → 调 graph → 消费 SSE
"""
import json
import re
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, AsyncIterator

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.conf.app_config import app_config
from app.core.log import logger
from app.rag.context import RagAgentContext
from app.rag.entities import DocParentChunk, DocSubChunk
from app.rag.graph import graph
from app.rag.metrics import rag_metrics
from app.rag.repositories import DocESRepository, DocSubChunkQdrantRepository
from app.rag.state import RagAgentState


# ---------------------------------------------------------------------------
# 切片工具函数
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """估算文本 token 数（中文约 1.5 字符/token）"""
    return int(len(text) / 1.5)


def _split_to_sub_chunks(parent: DocParentChunk) -> list[DocSubChunk]:
    """将父块切分为 256 token 子块，在句子边界截断"""
    content = parent.content
    max_tokens = app_config.rag.chunk.max_tokens
    sent_delimiters = app_config.rag.chunk.sentence_delimiters
    sent_pattern = re.compile(sent_delimiters)

    sentences = sent_pattern.split(content)
    sub_chunks: list[DocSubChunk] = []
    buffer = ""
    page = parent.page_number

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # 如果加当前句不超限，继续累积
        candidate = (buffer + "。" + sentence) if buffer else sentence
        if _estimate_tokens(candidate) <= max_tokens:
            buffer = candidate
        else:
            # 当前 buffer 不为空，先存档
            if buffer:
                sub_chunks.append(DocSubChunk(
                    id=f"sub_{uuid.uuid4().hex[:16]}",
                    parent_id=parent.id,
                    file_name=parent.file_name,
                    page_number=page,
                    content=buffer,
                    title_path=parent.title_path,
                ))
            buffer = sentence

    # 尾 buffer
    if buffer:
        sub_chunks.append(DocSubChunk(
            id=f"sub_{uuid.uuid4().hex[:16]}",
            parent_id=parent.id,
            file_name=parent.file_name,
            page_number=page,
            content=buffer,
            title_path=parent.title_path,
        ))

    return sub_chunks if sub_chunks else [DocSubChunk(
        id=f"sub_{uuid.uuid4().hex[:16]}",
        parent_id=parent.id,
        file_name=parent.file_name,
        page_number=page,
        content=content[:500],
        title_path=parent.title_path,
    )]


# ---------------------------------------------------------------------------
# 文档入库服务
# ---------------------------------------------------------------------------

class DocIngestionService:
    """文档入库服务：解析 → 切片 → 向量化 → 写入 Qdrant + ES"""

    def __init__(
        self,
        doc_qdrant_repository: DocSubChunkQdrantRepository,
        doc_es_repository: DocESRepository,
        embedding_client: HuggingFaceEndpointEmbeddings,
    ):
        self.qdrant_repo = doc_qdrant_repository
        self.es_repo = doc_es_repository
        self.embedding_client = embedding_client

    async def ensure_collections(self):
        """确保 Qdrant collection 和 ES index 已创建"""
        await self.qdrant_repo.ensure_sub_collection()
        await self.qdrant_repo.ensure_parent_collection()
        await self.es_repo.ensure_index()

    async def ingest_file(self, file_path: Path) -> dict[str, Any]:
        """解析一个文件，切片后写入 Qdrant + ES"""
        file_name = file_path.name
        logger.info(f"[RAG] 开始入库: {file_name}")

        # 1. 读取文件内容
        content = file_path.read_text(encoding="utf-8", errors="replace")

        # 2. 按空行/标题切分父块（简单实现：按 ## 标题或空行分割）
        parent_chunks = self._split_parents(file_name, str(file_path), content)

        # 3. 父块写入 Qdrant
        await self.qdrant_repo.upsert_parents(parent_chunks)

        # 4. 将父块切成子块
        all_sub_chunks: list[DocSubChunk] = []
        for parent in parent_chunks:
            all_sub_chunks.extend(_split_to_sub_chunks(parent))

        # 5. 子块向量化
        texts = [sc.content for sc in all_sub_chunks]
        embeddings = []
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_embs = await self.embedding_client.aembed_documents(batch_texts)
            embeddings.extend(batch_embs)

        # 6. 子块写入 Qdrant
        await self.qdrant_repo.upsert_sub_chunks(all_sub_chunks, embeddings)

        # 7. 子块写入 ES
        await self.es_repo.index_sub_chunks(all_sub_chunks)

        result = {
            "file_name": file_name,
            "parent_count": len(parent_chunks),
            "sub_chunk_count": len(all_sub_chunks),
            "status": "ready",
        }
        logger.info(f"[RAG] 入库完成: {result}")
        return result

    def _split_parents(self, file_name: str, file_path: str, content: str) -> list[DocParentChunk]:
        """按标题或空行切分父块"""
        lines = content.split("\n")
        parents: list[DocParentChunk] = []
        buffer: list[str] = []
        current_title = "（文档开头）"
        page = 1

        for line in lines:
            # 检测标题行（## 或 === 或 第X章）
            stripped = line.strip()
            title_match = re.match(r"^(#{1,4}\s+|第[一二三四五六七八九十\d]+[章节部篇])", stripped)
            if title_match and buffer:
                # 存档当前父块
                parents.append(DocParentChunk(
                    id=f"parent_{uuid.uuid4().hex[:16]}",
                    file_name=file_name,
                    file_path=file_path,
                    page_number=page,
                    title_path=current_title,
                    content="\n".join(buffer).strip(),
                    chunk_count=0,
                ))
                buffer = []
                current_title = stripped[:60]

            buffer.append(line)

        # 尾 buffer
        if buffer:
            parents.append(DocParentChunk(
                id=f"parent_{uuid.uuid4().hex[:16]}",
                file_name=file_name,
                file_path=file_path,
                page_number=page,
                title_path=current_title,
                content="\n".join(buffer).strip(),
                chunk_count=0,
            ))

        # 更新 chunk_count
        for p in parents:
            p.chunk_count = len(_split_to_sub_chunks(p))

        return parents


# ---------------------------------------------------------------------------
# RAG 问答服务
# ---------------------------------------------------------------------------

class RagQueryService:
    """RAG 问答：组装状态 → 调 graph → 消费 SSE"""

    def __init__(
        self,
        doc_qdrant_repository: DocSubChunkQdrantRepository,
        doc_es_repository: DocESRepository,
        embedding_client: HuggingFaceEndpointEmbeddings,
    ):
        self.doc_qdrant_repository = doc_qdrant_repository
        self.doc_es_repository = doc_es_repository
        self.embedding_client = embedding_client

    async def query(self, query: str, session_id: str | None = None) -> AsyncIterator[str]:
        """执行一次 RAG 问答，逐段产出 SSE 消息"""
        sid = session_id or f"session_{uuid.uuid4().hex[:8]}"

        state = RagAgentState(
            query=query,
            session_id=sid,
            keywords=[],
            retrieved_qdrant=[],
            retrieved_qdrant_scores=[],
            retrieved_bm25=[],
            retrieved_bm25_scores=[],
            retrieved_exact=[],
            context_chunks=[],
            assembled_context="",
            conversation_history=[],
            session_summary="",
            answer="",
            sources=[],
        )
        context = RagAgentContext(
            doc_qdrant_repository=self.doc_qdrant_repository,
            doc_es_repository=self.doc_es_repository,
            embedding_client=self.embedding_client,
        )

        rag_metrics.on_query_start()
        try:
            async for chunk in graph.astream(
                input=state, context=context, stream_mode="custom"
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:
            err_msg = str(e)
            if "connect" in err_msg.lower() or "timeout" in err_msg.lower():
                friendly = "知识库服务暂时不可用，请稍后重试。"
            elif "qdrant" in err_msg.lower():
                friendly = "向量检索服务异常，部分功能可能不可用。"
            elif "elasticsearch" in err_msg.lower() or "es" in err_msg.lower():
                friendly = "全文检索服务异常，部分功能可能不可用。"
            else:
                friendly = "系统内部错误，请稍后重试。"
            error = {"type": "error", "message": friendly, "detail": err_msg[:200]}
            yield f"data: {json.dumps(error, ensure_ascii=False, default=str)}\n\n"
        finally:
            rag_metrics.on_query_end()
