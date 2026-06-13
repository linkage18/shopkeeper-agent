"""
RAG Agent 状态定义

State 是 LangGraph 各节点之间传递和更新的共享数据。
三路并行召回后合并去重，经组装后生成带引用的回答。
"""
from typing import TypedDict

from app.rag.entities import DocParentChunk, DocSubChunk, SourceRef


class RagAgentState(TypedDict):
    """一次 RAG 问答链路中的核心状态"""

    # 输入
    query: str                           # 用户问题
    session_id: str                      # 会话 ID
    keywords: list[str]                  # 抽取的关键词

    # 三路并行召回结果（原始子块）
    retrieved_qdrant: list[DocSubChunk]  # Qdrant 向量召回
    retrieved_qdrant_scores: list[float]  # Qdrant 余弦相似度得分
    retrieved_bm25: list[DocSubChunk]    # ES BM25 召回
    retrieved_bm25_scores: list[float]   # ES BM25 原始得分
    retrieved_exact: list[DocSubChunk]   # MySQL 精确匹配召回

    # 合并截断后的有序上下文（已取父块）
    context_chunks: list[tuple[DocParentChunk, float]]  # [(父块, 最高子块得分)]
    assembled_context: str               # 拼好的 context prompt 段

    # 对话历史
    conversation_history: list[dict]     # 最近 N 轮 [{"role","content","sources"}]
    session_summary: str                 # 会话摘要（每 3 轮 LLM 压缩一次）

    # 输出
    answer: str                          # LLM 生成的回答
    sources: list[SourceRef]             # 溯源引用列表
