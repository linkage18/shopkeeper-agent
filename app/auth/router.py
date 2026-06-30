from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.jwt import create_token, verify_token
from app.auth.repository import AuthRepository
from app.auth.middleware import require_user
from app.clients.mysql_client_manager import meta_mysql_client_manager

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterReq(BaseModel):
    username: str = Field(..., min_length=2, max_length=32, pattern=r"^[a-zA-Z0-9_一-鿿]+$")
    password: str = Field(..., min_length=6, max_length=128)


class LoginReq(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=128)


async def get_auth_repo():
    async with meta_mysql_client_manager.session_factory() as session:
        yield AuthRepository(session)


@auth_router.post("/register")
async def register(req: RegisterReq, repo: Annotated[AuthRepository, Depends(get_auth_repo)]):
    result = await repo.register(req.username, req.password)
    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)
    token = create_token({"user_id": result.id, "username": result.username, "role": result.role})
    return {"token": token, "user": {"id": result.id, "username": result.username, "role": result.role}}


@auth_router.post("/login")
async def login(req: LoginReq, repo: Annotated[AuthRepository, Depends(get_auth_repo)]):
    user = await repo.login(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token({"user_id": user.id, "username": user.username, "role": user.role})
    return {"token": token, "user": {"id": user.id, "username": user.username, "role": user.role}}


me_router = APIRouter(tags=["me"])


@me_router.get("/api/auth/me")
async def me(request: Request):
    from app.auth.jwt import verify_token
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = verify_token(auth_header[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效")
    return {"user": payload}
