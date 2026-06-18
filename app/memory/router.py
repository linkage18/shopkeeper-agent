from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.middleware import require_admin
from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.memory.persistent import list_persistent, save_persistent, delete_persistent

memory_router = APIRouter(prefix="/api/memory", tags=["memory"])


class PersistentReq(BaseModel):
    id: str = ""
    category: str = "rule"
    name: str
    content: str
    priority: int = 0


async def get_db():
    async with meta_mysql_client_manager.session_factory() as session:
        yield session


@memory_router.get("/persistent")
async def list_persistent_api(
    user: Annotated[dict, Depends(require_admin)],
    session: Annotated[dict, Depends(get_db)],
):
    items = await list_persistent(session)
    return {"items": items}


@memory_router.post("/persistent")
async def save_persistent_api(
    req: PersistentReq,
    user: Annotated[dict, Depends(require_admin)],
    session: Annotated[dict, Depends(get_db)],
):
    entry = req.model_dump()
    if not entry["id"]:
        entry["id"] = f"pm_{uuid.uuid4().hex[:12]}"
    await save_persistent(session, entry)
    return {"status": "ok", "id": entry["id"]}


@memory_router.delete("/persistent/{entry_id}")
async def delete_persistent_api(
    entry_id: str,
    user: Annotated[dict, Depends(require_admin)],
    session: Annotated[dict, Depends(get_db)],
):
    await delete_persistent(session, entry_id)
    return {"status": "ok"}
