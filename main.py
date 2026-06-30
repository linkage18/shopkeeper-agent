"""
FastAPI 搴旂敤鍏ュ彛

璐熻矗鍒涘缓鍚庣搴旂敤瀹炰緥锛屾敞鍐屽簲鐢ㄧ敓鍛藉懆鏈熷嚱鏁帮紝骞舵妸鍚勪笟鍔℃ā鍧椾腑鐨?router
鎸傝浇鍒板悓涓€涓?app 涓娿€侶TTP 璇锋眰浼氬厛杩涘叆杩欓噷鍒涘缓鐨?app锛屽啀鎸夎矾鐢卞垎鍙戝埌
鍏蜂綋鐨勬帴鍙ｅ鐞嗗嚱鏁般€?"""

import uuid

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.api.routers.rag_query_router import rag_router, file_router
from app.auth.router import auth_router, me_router
from app.intent.router import intent_router
from app.memory.router import memory_router
from app.report_agent.router import report_agent_router
from app.report_agent.token_router import token_router
from app.schema_analyzer.router import schema_router, viz_router
from app.session.router import session_router
from app.cache.services import ensure_cache_collection
from app.core.context import request_id_ctx_var, user_ctx_var
from app.knowledge.router import knowledge_router
from app.reports.router import reports_router

# lifespan交给FastAPI管理
app = FastAPI(lifespan=lifespan)

# CORS — 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 鐭ヨ瘑璁板繂璺敱
app.include_router(knowledge_router)

# 娣卞害鍒嗘瀽璺敱
app.include_router(reports_router)

# 鏌ヨ璺敱锛歂L2SQL
app.include_router(query_router)

# 鏌ヨ璺敱锛歊AG 鐭ヨ瘑搴?
app.include_router(rag_router)

# 鏂囦欢涓婁紶璺敱锛歊AG 鐭ヨ瘑搴?
app.include_router(file_router)

app.include_router(intent_router)
app.include_router(memory_router)
app.include_router(report_agent_router)
app.include_router(token_router)
app.include_router(schema_router)
app.include_router(viz_router)
app.include_router(session_router)
app.include_router(auth_router)
app.include_router(me_router)
@app.get("/health")
async def health_check():
    """健康检查端点，供 Docker 编排和监控系统使用"""
    from app.clients.mysql_client_manager import (
        dw_mysql_client_manager,
        meta_mysql_client_manager,
    )
    from app.clients.qdrant_client_manager import qdrant_client_manager
    from app.clients.es_client_manager import es_client_manager

    status = {"status": "ok", "services": {}}
    all_ok = True

    # MySQL meta 库
    try:
        async with meta_mysql_client_manager.session_factory() as s:
            from sqlalchemy import text
            await s.execute(text("SELECT 1"))
        status["services"]["mysql_meta"] = "ok"
    except Exception as e:
        status["services"]["mysql_meta"] = f"error: {e}"
        all_ok = False

    # MySQL dw 库
    try:
        async with dw_mysql_client_manager.session_factory() as s:
            from sqlalchemy import text
            await s.execute(text("SELECT 1"))
        status["services"]["mysql_dw"] = "ok"
    except Exception as e:
        status["services"]["mysql_dw"] = f"error: {e}"
        all_ok = False

    # Qdrant
    try:
        client = qdrant_client_manager.client
        if client:
            await client.get_collections()
            status["services"]["qdrant"] = "ok"
        else:
            status["services"]["qdrant"] = "not_initialized"
            all_ok = False
    except Exception as e:
        status["services"]["qdrant"] = f"error: {e}"
        all_ok = False

    # Elasticsearch
    try:
        client = es_client_manager.client
        if client:
            await client.ping()
            status["services"]["es"] = "ok"
        else:
            status["services"]["es"] = "not_initialized"
            all_ok = False
    except Exception as e:
        status["services"]["es"] = f"error: {e}"
        all_ok = False

    from app.core.log import logger
    if not all_ok:
        status["status"] = "degraded"
        logger.warning(f"健康检查: 部分服务异常: {status}")
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=status)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=200, content=status)



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
    # request_id
    request_id = uuid.uuid4()
    ctx_token = request_id_ctx_var.set(str(request_id))
    try:
        response = await call_next(request)
        return response
    finally:
        request_id_ctx_var.reset(ctx_token)



