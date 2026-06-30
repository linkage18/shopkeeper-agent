"""
鐢靛晢闂暟 Agent 鍥剧紪鎺?
浣跨敤 LangGraph 鎶婇棶鏁版櫤鑳戒綋鐨勫悇涓妭鐐逛覆鎴愪竴鏉″彲瑙傛祴鐨勬墽琛岄摼璺?褰撳墠閾捐矾宸茬粡钀藉湴鍏抽敭璇嶆娊鍙栧拰澶氳矾鍙洖锛屽瓧娈靛拰鎸囨爣璧?Qdrant 鍚戦噺妫€绱紝瀛楁鍙栧€艰蛋 ES 鍏ㄦ枃妫€绱?鏁翠綋娴佺▼鍏堟娊鍙栫敤鎴烽棶棰樺叧閿瘝锛屽啀骞惰鍙洖瀛楁 瀛楁鍙栧€煎拰鎸囨爣淇℃伅锛?闅忓悗鍚堝苟鍙洖缁撴灉 杩囨护鍊欓€夎〃鍜屾寚鏍?琛ュ厖棰濆涓婁笅鏂囷紝鏈€鍚庣敓鎴?鏍￠獙 淇骞舵墽琛?SQL
"""

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from app.agent.context import DataAgentContext
from app.agent.nodes.add_extra_context import add_extra_context
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.extract_keywords import extract_keywords
from app.agent.nodes.filter_metric import filter_metric
from app.agent.nodes.filter_table import filter_table
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.merge_retrieved_info import merge_retrieved_info
from app.agent.nodes.recall_column import recall_column
from app.agent.nodes.recall_metric import recall_metric
from app.agent.nodes.recall_value import recall_value
from app.agent.nodes.run_sql import run_sql
from app.agent.nodes.validate_sql import validate_sql
from app.agent.state import DataAgentState

# StateGraph 澹版槑鏁村紶鍥句娇鐢ㄧ殑鐘舵€佺粨鏋勫拰杩愯鏃朵笂涓嬫枃缁撴瀯
graph_builder = StateGraph(state_schema=DataAgentState, context_schema=DataAgentContext)

# register nodes
graph_builder.add_node("extract_keywords", extract_keywords)
graph_builder.add_node("recall_column", recall_column)
graph_builder.add_node("recall_value", recall_value)
graph_builder.add_node("recall_metric", recall_metric)
graph_builder.add_node("merge_retrieved_info", merge_retrieved_info)
graph_builder.add_node("filter_metric", filter_metric)
graph_builder.add_node("filter_table", filter_table)
graph_builder.add_node("add_extra_context", add_extra_context)
graph_builder.add_node("generate_sql", generate_sql)
graph_builder.add_node("validate_sql", validate_sql)
graph_builder.add_node("correct_sql", correct_sql)
graph_builder.add_node("run_sql", run_sql)

# 浠庣敤鎴烽棶棰樺紑濮嬶紝鍏堟娊鍙栧叧閿瘝浣滀负鍚庣画妫€绱㈢殑鍩虹
graph_builder.add_edge(START, "extract_keywords")

# 鍏抽敭璇嶆娊鍙栧悗骞惰杩涘叆涓夌被鍙洖锛屽垎鍒潰鍚戝瓧娈?瀛楁鍊煎拰涓氬姟鎸囨爣
graph_builder.add_edge("extract_keywords", "recall_column")
graph_builder.add_edge("extract_keywords", "recall_value")
graph_builder.add_edge("extract_keywords", "recall_metric")

# 涓夎矾鍙洖閮藉畬鎴愬悗锛屽啀杩涘叆缁熶竴鐨勪俊鎭悎骞惰妭鐐?graph_builder.add_edge("recall_column", "merge_retrieved_info")
graph_builder.add_edge("recall_value", "merge_retrieved_info")
graph_builder.add_edge("recall_metric", "merge_retrieved_info")

# 鍚堝苟鍚庣殑鍊欓€変俊鎭户缁媶鎴愯〃杩囨护鍜屾寚鏍囪繃婊や袱鏉＄嚎
graph_builder.add_edge("merge_retrieved_info", "filter_table")
graph_builder.add_edge("merge_retrieved_info", "filter_metric")

# 琛ㄥ拰鎸囨爣閮借繃婊ゅ畬鎴愬悗锛岀粺涓€琛ュ厖鐢熸垚 SQL 鎵€闇€鐨勪笂涓嬫枃
graph_builder.add_edge("filter_table", "add_extra_context")
graph_builder.add_edge("filter_metric", "add_extra_context")
graph_builder.add_edge("add_extra_context", "generate_sql")
graph_builder.add_edge("generate_sql", "validate_sql")

# SQL 鏍￠獙閫氳繃灏辩洿鎺ユ墽琛岋紝鏍￠獙澶辫触鍒欒繘鍏ヤ慨姝ｈ妭鐐癸紙鏈€澶?2 娆￠噸璇曪級
# 淇瀹屾垚鍚庡洖鍒?validate_sql 閲嶆柊鏍￠獙
def _validate_route(state: DataAgentState) -> str:
    """鏉′欢杈癸細鏍￠獙缁撴灉 + 閲嶈瘯娆℃暟鍐冲畾娴佺▼璧板悜"""
    if state["error"] is None:
        return "run_sql"
    retry = state.get("retry_count", 0)
    if retry < 2:
        return "correct_sql"
    # 閲嶈瘯鐢ㄥ敖锛岃褰曟渶缁堥敊璇苟杩涘叆 run_sql锛堟惡甯﹀弸濂芥彁绀猴級
    state["fatal_error"] = f"SQL 鏍￠獙澶辫触锛堝凡閲嶈瘯 {retry} 娆★級锛岄敊璇? {state['error']}"
    return "run_sql"

graph_builder.add_conditional_edges(
    source="validate_sql",
    path=_validate_route,
    path_map={"run_sql": "run_sql", "correct_sql": "correct_sql"},
)
graph_builder.add_edge("correct_sql", "validate_sql")
graph_builder.add_edge("run_sql", END)

# 缂栬瘧鍚庣殑 graph 鏄澶栦娇鐢ㄧ殑 Agent 鎵ц鍏ュ彛
# 改为懒加载 + 可注入，测试时可通过 override_graph() 替换
_graph_instance = None

def get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = graph_builder.compile()
    return _graph_instance

def override_graph(mock_graph):
    global _graph_instance
    _graph_instance = mock_graph

# print(graph.get_graph().draw_mermaid())


