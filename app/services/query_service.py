"""
问数查询服务

负责把 API 层传入的自然语言问题转换成一次 LangGraph 工作流执行：
创建初始 State、组装 Runtime Context、消费 get_graph().astream 的流式输出，
并统一包装成 SSE 文本返回给路由层。
"""

import json

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.agent.context import DataAgentContext
from app.agent.graph import get_graph
from app.agent.state import DataAgentState
from app.repositories.es.value_es_repository import ValueESRepository
import uuid
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class QueryService:
    """封装一次问数查询所需的业务编排逻辑"""

    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        embedding_client: HuggingFaceEndpointEmbeddings,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
    ):
        # MySQL 仓储分别负责元数据补全和真实数仓环境信息读取
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository

        # 召回链路依赖的向量检索、Embedding 和全文检索能力由依赖层注入
        self.embedding_client = embedding_client
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(self, query: str, user_id: str = ""):
        """执行一次问数工作流，并逐段产出 SSE 消息"""

        # 语义缓存命中 → 直接返回
        from app.cache.services import semantic_cache_search, exact_cache_get
        cached = await semantic_cache_search(query) or exact_cache_get(query)
        if cached:
            yield f"data: {json.dumps({'type': 'result', 'data': cached, 'from_cache': True}, ensure_ascii=False)}\n\n"
            return

        # 多层级联记忆检索（每次从磁盘/数据库重新读取）
        augmented_query = query
        memory_ctx = ""

        # State 只放会被图节点读写和合并的业务数据，外部工具对象不塞进 State
        state = DataAgentState(query=augmented_query)
        # Context 保存本次图执行需要复用的外部依赖，节点通过 runtime.context 读取
        context = DataAgentContext(
            column_qdrant_repository=self.column_qdrant_repository,
            embedding_client=self.embedding_client,
            metric_qdrant_repository=self.metric_qdrant_repository,
            value_es_repository=self.value_es_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
        )
        last_result = None
        try:
            # stream_mode="custom" 对应节点内部 writer(...) 写出的进度消息
            async for chunk in get_graph().astream(
                input=state, context=context, stream_mode="custom"
            ):
                # SSE 要求每条消息以 data: 开头，并以两个换行符结束
                # ensure_ascii=False 保留中文进度文案，default=str 兜底处理日期等非 JSON 类型
                if chunk.get("type") == "result":
                    last_result = chunk.get("data")
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
            # 缓存结果（精确缓存 + Qdrant 语义缓存）
            if last_result:
                from app.cache.services import exact_cache_set, semantic_cache_save
                exact_cache_set(query, last_result)
                try:
                    await semantic_cache_save(query, last_result)
                except Exception as e:
                    from app.core.log import logger
                    logger.warning(f"Cache save failed: {e}")
                # 知识提取：对话中识别业务口径定义
                try:
                    from app.knowledge.extractor import extract_knowledge
                    sql = last_result.get("sql", "") if isinstance(last_result, dict) else ""
                    data = last_result.get("rows", last_result) if isinstance(last_result, dict) else last_result
                    await extract_knowledge(query, sql, str(data)[:500], user_id)
                except Exception as e:
                    from app.core.log import logger
                    logger.warning(f"Knowledge extraction failed: {e}")
        except Exception as e:
            # 流式接口已经开始返回后不能再改 HTTP 状态码，因此把异常也包装成一条 SSE 消息
            err_msg = str(e)
            if "connect" in err_msg.lower() or "timeout" in err_msg.lower():
                friendly = "数据库服务暂时不可用，请稍后重试。"
            else:
                friendly = "查询过程出现异常，请稍后重试。"
            error = {"type": "error", "message": friendly, "detail": err_msg[:200]}
            yield f"data: {json.dumps(error, ensure_ascii=False, default=str)}\n\n"



