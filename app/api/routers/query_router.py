"""
问数查询接口路由

负责定义前端访问的 `/api/query` 接口，把 HTTP 请求交给 QueryService，
并把问数智能体执行过程以 SSE 形式持续返回给客户端。
路由层只处理请求体、依赖声明和响应类型，不直接创建 Repository 或执行图节点。
"""
import re

from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse
from typing import Annotated
from fastapi import Depends

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.core.context import user_ctx_var
from app.services.query_service import QueryService

# 当前模块只维护查询相关接口，避免后续所有 API 都挤在 main.py 中
query_router = APIRouter()

# 破坏性意图检测规则：在进入 LangGraph 前拦截
_SQL_DESTRUCTIVE_PATTERNS = [
    re.compile(r"(修改|更新|更改|编辑|改|变更)\s*.{0,10}(数据|记录|信息|订单|用户|表)"),
    re.compile(r"(删除|移除|清空|清除|删掉|去掉|销毁|丢弃)\s*.{0,10}(数据|记录|信息|订单|用户|表)"),
    re.compile(r"(插入|新增|添加|写入|创建|建立|生成)\s*.{0,10}(数据|记录|信息|订单|用户)"),
    re.compile(r"(drop|delete|update|insert|truncate|alter)\s", re.IGNORECASE),
    re.compile(r"修改一条数据"),
]


@query_router.post("/api/query")
async def query_handler(
    # 请求体参数：FastAPI 会把前端 JSON 自动解析成 QuerySchema
    query: QuerySchema,
    # 服务依赖：FastAPI 会调用 get_query_service，递归组装它所需的仓储和客户端
    query_service: Annotated[QueryService, Depends(get_query_service)],
):
    """接收用户自然语言问题，并流式返回 LangGraph 工作流输出"""

    # 频率限制
    from app.cache.services import check_rate_limit
    if not check_rate_limit("default"):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    # 破坏性意图提前阻断：不进入 LangGraph 流程
    for pattern in _SQL_DESTRUCTIVE_PATTERNS:
        if pattern.search(query.query):
            raise HTTPException(
                status_code=400,
                detail="仅支持查询操作，已自动阻断（检测到疑似数据修改意图）",
            )

    user = user_ctx_var.get()
    user_id = user.get("user_id", "") if user else ""

    return StreamingResponse(
        # query.query 是用户问题字符串；QueryService.query 返回异步生成器供响应逐段消费
        query_service.query(query.query, user_id=user_id),
        media_type="text/event-stream",
    )
