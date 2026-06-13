"""
RAG 问答 Agent 图编排

使用 LangGraph 把关键词抽取、多路召回、上下文组装和回答生成
串成一条可观测的执行链路。
"""
import asyncio

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from app.rag.context import RagAgentContext
from app.rag.nodes import (
    assemble_context,
    extract_keywords,
    generate_answer,
    recall_docs,
)
from app.rag.state import RagAgentState

# 声明 StateGraph
graph_builder = StateGraph(
    state_schema=RagAgentState, context_schema=RagAgentContext
)

# 注册节点
graph_builder.add_node("extract_keywords", extract_keywords)
graph_builder.add_node("recall_docs", recall_docs)
graph_builder.add_node("assemble_context", assemble_context)
graph_builder.add_node("generate_answer", generate_answer)

# 编排链路
graph_builder.add_edge(START, "extract_keywords")
graph_builder.add_edge("extract_keywords", "recall_docs")
graph_builder.add_edge("recall_docs", "assemble_context")
graph_builder.add_edge("assemble_context", "generate_answer")
graph_builder.add_edge("generate_answer", END)

# 编译图
graph = graph_builder.compile()

# 打印图结构
# print(graph.get_graph().draw_mermaid())

if __name__ == "__main__":

    async def test():
        """本地调试 RAG 问答链路"""
        from app.clients.embedding_client_manager import embedding_client_manager
        from app.clients.es_client_manager import es_client_manager
        from app.clients.qdrant_client_manager import qdrant_client_manager
        from app.rag.repositories import DocESRepository, DocSubChunkQdrantRepository

        # 初始化客户端
        qdrant_client_manager.init()
        embedding_client_manager.init()
        es_client_manager.init()

        # 创建仓储
        doc_qdrant_repo = DocSubChunkQdrantRepository(qdrant_client_manager.client)
        doc_es_repo = DocESRepository(es_client_manager.client)

        context = RagAgentContext(
            doc_qdrant_repository=doc_qdrant_repo,
            doc_es_repository=doc_es_repo,
            embedding_client=embedding_client_manager.client,
        )

        state = RagAgentState(
            query="项目使用什么技术栈？",
            session_id="test-001",
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

        print("=" * 60)
        print(f"问题: {state['query']}")
        print("=" * 60)

        async for chunk in graph.astream(
            input=state, context=context, stream_mode="custom"
        ):
            if chunk.get("type") == "progress":
                print(f"  [{chunk['status']}] {chunk['step']}")
            elif chunk.get("type") == "result":
                print(f"\n回答: {chunk['answer']}")
                for s in chunk.get("sources", []):
                    print(f"  来源: {s['file_name']}, P{s['page_number']}")

        # 关闭客户端
        await qdrant_client_manager.close()
        await es_client_manager.close()

    asyncio.run(test())
