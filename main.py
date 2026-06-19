"""
FastAPI 应用入口

负责创建后端应用实例，注册应用生命周期函数，并把各业务模块中的 router
挂载到同一个 app 上。HTTP 请求会先进入这里创建的 app，再按路由分发到
具体的接口处理函数。
"""

import uuid

from fastapi import FastAPI, Request

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.api.routers.rag_query_router import rag_router, file_router
from app.auth.router import auth_router, me_router
from app.intent.router import intent_router
from app.memory.router import memory_router
from app.report_agent.router import report_agent_router
from app.report_agent.token_router import token_router
from app.schema_analyzer.router import schema_router, viz_router
from app.cache.services import ensure_cache_collection
from app.core.context import request_id_ctx_var, user_ctx_var
from app.knowledge.router import knowledge_router
from app.reports.router import reports_router

# lifespan 交给 FastAPI 管理，用于在服务启动和关闭时统一初始化与释放外部客户端
app = FastAPI(lifespan=lifespan)

# 知识记忆路由
app.include_router(knowledge_router)

# 深度分析路由
app.include_router(reports_router)

# 查询路由：NL2SQL
app.include_router(query_router)

# 查询路由：RAG 知识库
app.include_router(rag_router)

# 文件上传路由：RAG 知识库
app.include_router(file_router)

app.include_router(intent_router)
app.include_router(memory_router)
app.include_router(report_agent_router)
app.include_router(token_router)
app.include_router(schema_router)
app.include_router(viz_router)
app.include_router(auth_router)
app.include_router(me_router)


@app.middleware("http")
async def auth_middleware_inline(request: Request, call_next):
    from app.auth.jwt import verify_token
    auth_header = request.headers.get("authorization", "")
    ctx_token = None
    if auth_header.startswith("Bearer "):
        payload = verify_token(auth_header[7:])
        if payload:
            request.state.user = payload
            ctx_token = user_ctx_var.set(payload)
    try:
        response = await call_next(request)
        return response
    finally:
        if ctx_token is not None:
            user_ctx_var.reset(ctx_token)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    # 请求被处理之前
    request_id = uuid.uuid4()
    ctx_token = request_id_ctx_var.set(str(request_id))
    try:
        response = await call_next(request)
        return response
    finally:
        request_id_ctx_var.reset(ctx_token)


