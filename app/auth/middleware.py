from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from app.auth.jwt import verify_token
from app.core.context import user_ctx_var


async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/auth/"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = verify_token(token)
        if payload:
            user_ctx_var.set(payload)
            response = await call_next(request)
            return response

    user_ctx_var.set(None)
    return await call_next(request)


async def require_user(user_data: dict | None = None):
    user = user_ctx_var.get()
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return user


async def require_admin(user: dict = None):
    u = await require_user()
    if u.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return u
