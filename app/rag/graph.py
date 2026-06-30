"""
RAG 闂瓟 Agent 鍥剧紪鎺?
浣跨敤 LangGraph 鎶婂叧閿瘝鎶藉彇銆佸璺彫鍥炪€佷笂涓嬫枃缁勮鍜屽洖绛旂敓鎴?涓叉垚涓€鏉″彲瑙傛祴鐨勬墽琛岄摼璺€?"""
import asyncio

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from app.rag.context import RagAgentContext
from app.rag.nodes import (
    post_process,
    assemble_context,
    extract_keywords,
    generate_answer,
    recall_docs,
)
from app.rag.state import RagAgentState

# 澹版槑 StateGraph
graph_builder = StateGraph(
    state_schema=RagAgentState, context_schema=RagAgentContext
)

# 娉ㄥ唽鑺傜偣
graph_builder.add_node("extract_keywords", extract_keywords)
graph_builder.add_node("recall_docs", recall_docs)
graph_builder.add_node("assemble_context", assemble_context)
graph_builder.add_node("generate_answer", generate_answer)
graph_builder.add_node("post_process", post_process)

# 缂栨帓閾捐矾
graph_builder.add_edge(START, "extract_keywords")
graph_builder.add_edge("extract_keywords", "recall_docs")
graph_builder.add_edge("recall_docs", "assemble_context")
graph_builder.add_edge("assemble_context", "generate_answer")
graph_builder.add_edge("generate_answer", "post_process")
graph_builder.add_edge("post_process", END)

# compile graph
graph = graph_builder.compile()

# 鎵撳嵃鍥剧粨鏋?# print(graph.get_graph().draw_mermaid())

