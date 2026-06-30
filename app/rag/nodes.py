"""
RAG Agent 节点定义

每个节点是一个 async function，接收 state + runtime，返回 state 更新。
节点之间通过 StateGraph 编排，不直接互相调用。
"""
import asyncio
import time

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.llm import get_llm
from app.conf.app_config import app_config
from app.core.keywords import extract_keywords as _extract_keywords
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt
from app.rag.context import RagAgentContext
from app.rag.entities import DocParentChunk, DocSubChunk, SourceRef
from app.rag.metrics import rag_metrics
from app.rag.state import RagAgentState


# ===================================================================
# 节点 1：关键词抽取
# ===================================================================

async def extract_keywords(state: RagAgentState, runtime: Runtime[RagAgentContext]):
    """从用户问题中抽取关键词，供后续三路召回使用"""
    writer = runtime.stream_writer
    step = "抽取关键词"
    writer({"type": "progress", "step": step, "status": "running"})
    rag_metrics.on_node_start(step)

    try:
        query = state["query"]
        keywords = _extract_keywords(query)

        writer({"type": "progress", "step": step, "status": "success"})
        rag_metrics.on_node_end(step, "success")
        logger.info(f"[RAG] 抽取关键词: {keywords}")
        return {"keywords": keywords}
    except Exception as e:
        logger.error(f"[RAG] 关键词抽取失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        rag_metrics.on_node_end(step, "error")
        raise


# ===================================================================
# 节点 2：三路召回
# ===================================================================

async def recall_docs(state: RagAgentState, runtime: Runtime[RagAgentContext]):
    """三路并行召回：Qdrant 向量 + ES BM25 + embedding 向量"""
    writer = runtime.stream_writer
    step = "召回文档"
    writer({"type": "progress", "step": step, "status": "running"})
    rag_metrics.on_node_start(step)

    try:
        keywords = state["keywords"]
        query = state["query"]
        ctx = runtime.context
        qdrant_repo = ctx["doc_qdrant_repository"]
        es_repo = ctx["doc_es_repository"]
        embedding_client = ctx["embedding_client"]

        # 熔断检查：两路都已熔断则跳过检索
        if rag_metrics.is_circuit_open("qdrant") and rag_metrics.is_circuit_open("es"):
            logger.warning("[CIRCUIT] 两路均已熔断，跳过检索")
            rag_metrics.on_recall_result(0, 0)
            writer({"type": "progress", "step": step, "status": "success"})
            rag_metrics.on_node_end(step, "success")
            return {"retrieved_qdrant": [], "retrieved_qdrant_scores": [], "retrieved_bm25": [], "retrieved_bm25_scores": []}

        # 两路各自独立容错：一路失败不影响另一路
        async def recall_qdrant():
            try:
                embedding = await embedding_client.aembed_query(query)
                results = await qdrant_repo.search_sub_chunks(embedding)
                rag_metrics.record_recall_success("qdrant")
                return results
            except Exception as e:
                rag_metrics.record_recall_failure("qdrant")
                logger.error(f"[RAG] Qdrant 召回失败（不影响整体流程）: {e}")
                return []

        async def recall_bm25():
            try:
                kw_query = " ".join(keywords[:5])
                results = await es_repo.search(kw_query)
                rag_metrics.record_recall_success("es")
                return results
            except Exception as e:
                rag_metrics.record_recall_failure("es")
                logger.error(f"[RAG] ES 召回失败（不影响整体流程）: {e}")
                return []

        qdrant_task = recall_qdrant()
        bm25_task = recall_bm25()

        qdrant_results, bm25_results = await asyncio.gather(
            qdrant_task, bm25_task, return_exceptions=True
        )

        # 兜底处理 gather 返回的异常
        qdrant_results = qdrant_results if not isinstance(qdrant_results, Exception) else []
        bm25_results = bm25_results if not isinstance(bm25_results, Exception) else []

        # 采集召回指标
        qdrant_count = len(qdrant_results)
        es_count = len(bm25_results)
        rag_metrics.on_recall_result(qdrant_count, es_count)

        writer({"type": "progress", "step": step, "status": "success"})
        rag_metrics.on_node_end(step, "success")
        logger.info(f"[RAG] 召回结果: Qdrant={qdrant_count}条, ES={es_count}条")
        return {
            "retrieved_qdrant": [chunk for chunk, _ in qdrant_results] if qdrant_results else [],
            "retrieved_qdrant_scores": [score for _, score in qdrant_results] if qdrant_results else [],
            "retrieved_bm25": [chunk for chunk, _ in bm25_results] if bm25_results else [],
            "retrieved_bm25_scores": [score for _, score in bm25_results] if bm25_results else [],
        }
    except Exception as e:
        logger.error(f"[RAG] 召回失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        rag_metrics.on_node_end(step, "error")
        raise


# ===================================================================
# 节点 3：上下文组装
# ===================================================================

async def assemble_context(state: RagAgentState, runtime: Runtime[RagAgentContext]):
    """合并三路召回结果，去重、截断、取父块、拼 context prompt"""
    writer = runtime.stream_writer
    step = "组装上下文"
    writer({"type": "progress", "step": step, "status": "running"})
    rag_metrics.on_node_start(step)

    try:
        ctx = runtime.context
        qdrant_repo = ctx["doc_qdrant_repository"]

        # 1. 合并去重，使用真实得分
        import math
        seen_ids: set[str] = set()
        scored: list[tuple[DocSubChunk, float]] = []

        qdrant_chunks = state.get("retrieved_qdrant", [])
        qdrant_scores = state.get("retrieved_qdrant_scores", [])
        for chunk, score in zip(qdrant_chunks, qdrant_scores):
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                scored.append((chunk, score))  # Qdrant 余弦相似度 [0,1]，直接用

        bm25_chunks = state.get("retrieved_bm25", [])
        bm25_scores = state.get("retrieved_bm25_scores", [])
        for chunk, score in zip(bm25_chunks, bm25_scores):
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                # ES BM25 得分范围 [0,20+]，sigmoid(score/5) 映射到 [0,1]
                norm_score = 1.0 / (1.0 + math.exp(-score / 5.0))
                scored.append((chunk, norm_score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # 2. 检查最高分
        cfg = app_config.rag
        if not scored or scored[0][1] < cfg.retrieval.score_threshold:
            rag_metrics.on_context_assembled(0, 0)
            writer({"type": "progress", "step": step, "status": "success"})
            rag_metrics.on_node_end(step, "success")
            logger.info("[RAG] 所有召回结果得分低于阈值，context 留空")
            return {"context_chunks": [], "assembled_context": ""}

        # 3. 按 parent_id 分组
        parent_best_score: dict[str, float] = {}
        for chunk, score in scored:
            pid = chunk.parent_id
            if pid not in parent_best_score or score > parent_best_score[pid]:
                parent_best_score[pid] = score

        parent_ids = list(parent_best_score.keys())
        parent_map = await qdrant_repo.get_parents_batch(parent_ids)

        scored_parents: list[tuple[DocParentChunk, float]] = []
        for pid, score in sorted(parent_best_score.items(), key=lambda x: x[1], reverse=True):
            if pid in parent_map:
                scored_parents.append((parent_map[pid], score))

        # 4. 按 token 上限截断
        max_tokens = cfg.context.max_tokens
        selected_parents: list[tuple[DocParentChunk, float]] = []
        total_chars = 0
        for parent, score in scored_parents:
            char_len = len(parent.content)
            if total_chars + char_len <= max_tokens * 1.5:
                selected_parents.append((parent, score))
                total_chars += char_len
            else:
                break

        # 5. 拼 context
        context_lines = []
        for idx, (parent, score) in enumerate(selected_parents, 1):
            snippet = parent.content[:300] + "..." if len(parent.content) > 300 else parent.content
            context_lines.append(
                f"[{idx}] (得分 {score:.2f}) {snippet}\n"
                f"    [来源: {parent.file_name}, P{parent.page_number}]"
            )
        assembled_context = "\n\n".join(context_lines)

        # 采集上下文指标
        rag_metrics.on_context_assembled(len(selected_parents), len(assembled_context))

        writer({"type": "progress", "step": step, "status": "success"})
        rag_metrics.on_node_end(step, "success")
        logger.info(f"[RAG] 上下文组装完成: {len(selected_parents)}个父块, {len(assembled_context)}字符")
        return {
            "context_chunks": selected_parents,
            "assembled_context": assembled_context,
        }
    except Exception as e:
        logger.error(f"[RAG] 上下文组装失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        rag_metrics.on_node_end(step, "error")
        raise


# ===================================================================
# 节点 4：生成回答
# ===================================================================

async def generate_answer(state: RagAgentState, runtime: Runtime[RagAgentContext]):
    """基于上下文生成带引用的回答"""
    writer = runtime.stream_writer
    step = "生成答案"
    writer({"type": "progress", "step": step, "status": "running"})
    rag_metrics.on_node_start(step)

    try:
        query = state["query"]
        context = state.get("assembled_context", "")
        history = state.get("conversation_history", [])
        session_summary = state.get("session_summary", "")

        history_cfg = app_config.rag.context
        recent_history = history[-history_cfg.history_max_rounds * 2:] if history else []
        history_lines = []
        for msg in recent_history:
            role = "用户" if msg.get("role") == "user" else "助手"
            history_lines.append(f"{role}: {msg.get('content', '')}")
        # 如果存在会话摘要，优先使用摘要 + 最近一轮
        if session_summary:
            history_text = (
                f"[会话摘要]\n{session_summary}\n\n"
                f"[最近对话]\n" + "\n".join(history_lines[-2:])
            )
        else:
            history_text = "\n".join(history_lines)

        if not context.strip():
            answer = "知识库中未找到与问题相关的信息。"
            rag_metrics.on_answer_generated(answer, 0)
            writer({"type": "progress", "step": step, "status": "success"})
            rag_metrics.on_node_end(step, "success")
            writer({"type": "result", "answer": answer, "sources": []})
            return {"answer": answer, "sources": []}

        prompt = PromptTemplate(
            template=(
                "<system>你是一个企业知识库助手。严格依据以下文档片段回答问题。\n"
                "若无法从片段中找到答案，请如实说\"未找到相关信息\"。\n"
                "引用格式：[来源: 文件名, 页码Pxx]\n\n"
                "请在回答中标注引用编号 [1]、[2] 等，每个引用对应一个来源。</system>\n\n"
                "<context>\n{context}\n</context>\n\n"
                "<history>\n{history}\n</history>\n\n"
                "<question>\n{query}\n</question>\n\n"
                "回答："
            ),
            input_variables=["context", "history", "query"],
        )
        chain = prompt | get_llm() | StrOutputParser()

        result_text = await chain.ainvoke({
            "context": context,
            "history": history_text or "（无）",
            "query": query,
        })

        context_chunks = state.get("context_chunks", [])
        # 最多取前 5 个得分最高的来源，避免来源列表过长
        top_chunks = context_chunks[:5]
        sources = [
            SourceRef(
                file_name=parent.file_name,
                page_number=parent.page_number,
                snippet=parent.content[:120],
                score=score,
            )
            for parent, score in top_chunks
        ]

        # 采集生成指标
        rag_metrics.on_answer_generated(result_text, len(sources))

        writer({"type": "progress", "step": step, "status": "success"})
        rag_metrics.on_node_end(step, "success")
        writer({
            "type": "result",
            "answer": result_text,
            "sources": [s.__dict__ for s in sources],
        })

        logger.info(f"[RAG] 回答生成完成, {len(sources)}个引用")

        from app.rag.hooks import execute_post_hooks

        return {
            "answer": result_text,
            "sources": sources,
        }
    except Exception as e:
        logger.error(f"[RAG] 回答生成失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        rag_metrics.on_node_end(step, "error")
        raise

async def post_process(state: RagAgentState, runtime: Runtime[RagAgentContext]):
    """后置处理节点：更新对话历史、生成摘要、持久化

    从 generate_answer 中分离出来，作为独立节点在图中执行。
    失败不影响已有的回答内容。
    """
    from app.rag.hooks import execute_post_hooks
    from app.core.log import logger

    answer = state.get("answer", "")
    sources = state.get("sources", [])

    try:
        updated_state = await execute_post_hooks(dict(state), answer, sources)
    except Exception as e:
        logger.warning(f"[RAG] 后置处理失败（不影响已有回答）: {e}")
        updated_state = dict(state)

    return {
        "conversation_history": updated_state.get("conversation_history", []),
        "session_summary": updated_state.get("session_summary", ""),
    }
