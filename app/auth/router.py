from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.jwt import create_token
from app.auth.repository import AuthRepository
from app.auth.middleware import require_user
from app.clients.mysql_client_manager import meta_mysql_client_manager

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterReq(BaseModel):
    username: str
    password: str


class LoginReq(BaseModel):
    username: str
    password: str


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


@auth_router.get("/me")
async def me(user: Annotated[dict, Depends(require_user)]):
    return {"user": user}
