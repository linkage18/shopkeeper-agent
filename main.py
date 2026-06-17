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
from app.auth.middleware import auth_middleware
from app.auth.router import auth_router
from app.cache.services import ensure_cache_collection
from app.core.context import request_id_ctx_var
from app.knowledge.router import knowledge_router
from app.reports.router import reports_router

# lifespan 交给 FastAPI 管理，用于在服务启动和关闭时统一初始化与释放外部客户端
app = FastAPI(lifespan=lifespan)

# 认证路由
app.include_router(auth_router)

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


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    # 请求被处理之前
    request_id = uuid.uuid4()
    request_id_ctx_var.set(request_id)
    response = await call_next(request)
    # 请求被处理之后
    return response


@app.middleware("http")
async def auth(request: Request, call_next):
    response = await auth_middleware(request, call_next)
    return response
