from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.auth.middleware import require_user, require_admin
from app.knowledge.manager import list_knowledge, get_knowledge, save_knowledge, delete_knowledge, search_knowledge
from app.knowledge.models import KnowledgeEntry
from app.core.context import user_ctx_var
from datetime import datetime

knowledge_router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@knowledge_router.get("/list")
async def list_knowledge_api(user: Annotated[dict, Depends(require_user)]):
    is_admin = user.get("role") == "admin"
    items = list_knowledge(is_admin=is_admin, user_id=user.get("user_id", ""))
    return {"items": items}


@knowledge_router.get("/get/{title}")
async def get_knowledge_api(title: str, user: Annotated[dict, Depends(require_user)]):
    entry = get_knowledge(title, user.get("user_id", ""))
    if not entry:
        raise HTTPException(status_code=404, detail="知识不存在")
    return {"entry": entry}


@knowledge_router.post("/save")
async def save_knowledge_api(data: dict, user: Annotated[dict, Depends(require_user)]):
    is_shared = data.get("scope", "shared") == "shared"
    if is_shared and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以修改共享知识")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = KnowledgeEntry(
        title=data["title"],
        definition=data.get("definition", ""),
        tables=data.get("tables", []),
        example_sql=data.get("example_sql", ""),
        tags=data.get("tags", []),
        created_by=user.get("username", ""),
        created_at=now,
        status=data.get("status", "approved"),
    )
    save_knowledge(entry, user.get("user_id", ""), is_shared=is_shared)
    return {"status": "ok"}


@knowledge_router.delete("/delete/{title}")
async def delete_knowledge_api(title: str, user: Annotated[dict, Depends(require_user)], data: dict = {}):
    is_shared = data.get("scope", "shared") == "shared"
    if is_shared and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以删除共享知识")
    ok = delete_knowledge(title, user.get("user_id", ""), is_shared=is_shared)
    if not ok:
        raise HTTPException(status_code=404, detail="知识不存在")
    return {"status": "ok"}


@knowledge_router.get("/search")
async def search_knowledge_api(q: str, user: Annotated[dict, Depends(require_user)]):
    results = search_knowledge(q, user.get("user_id", ""))
    return {"items": results}
