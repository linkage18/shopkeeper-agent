from fastapi import Request, HTTPException

from app.auth.jwt import verify_token


async def auth_middleware(request: Request, call_next):
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        payload = verify_token(auth_header[7:])
        if payload:
            request.state.user = payload
    response = await call_next(request)
    return response


async def require_user(request: Request):
    # 优先从 request.state 读（middleware 设置），否则直接从 header 解析
    user = getattr(request.state, "user", None)
    if user:
        return user
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        payload = verify_token(auth_header[7:])
        if payload:
            return payload
    raise HTTPException(status_code=401, detail="未登录")


async def require_admin(request: Request):
    u = await require_user(request)
    if u.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return u
