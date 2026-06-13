"""
RAG 业务实体定义

父子索引结构：子块用于检索（细粒度），父块用于生成（上下文完整度）
"""
from dataclasses import dataclass, field


@dataclass
class DocParentChunk:
    """父块：按标题层级聚合的完整段落，用于 LLM 上下文"""
    id: str                     # f"parent_{uuid7}"
    file_name: str              # 来源文件名
    file_path: str              # 来源文件路径
    page_number: int            # 起始页码
    title_path: str             # 标题层级路径，如 "第3章 > 3.2 > 配置说明"
    content: str                # 完整段落原文
    chunk_count: int            # 包含子块数


@dataclass
class DocSubChunk:
    """子块：256 token 粒度的检索单元，用于向量/全文检索"""
    id: str                     # f"sub_{uuid7}"
    parent_id: str              # 关联的父块 ID → DocParentChunk.id
    file_name: str              # 来源文件名
    page_number: int            # 来源页码
    content: str                # 子块原文
    title_path: str = ""        # 冗余存储，方便检索时快速获取标题路径


@dataclass
class SourceRef:
    """答案溯源引用"""
    file_name: str
    page_number: int
    snippet: str                # 引用片段（前 120 字）
    score: float
