"""
Token 统计路由
"""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.middleware import require_user
from app.report_agent.token_counter import token_counter

token_router = APIRouter(prefix="/api/token", tags=["token"])


@token_router.get("/usage")
async def get_token_usage(user: Annotated[dict, Depends(require_user)]):
    session_id = user.get("user_id", "default")
    usage = token_counter.get_session_usage(session_id)
    return {"session_id": session_id, **usage}


@token_router.get("/summary")
async def get_token_summary(user: Annotated[dict, Depends(require_user)]):
    return token_counter.get_summary()
