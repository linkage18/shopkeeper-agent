import hashlib
import json
import time
from typing import Any

from app.clients.qdrant_client_manager import qdrant_client_manager
from app.clients.embedding_client_manager import embedding_client_manager

CACHE_COLLECTION = "query_cache"
_cache: dict[str, dict] = {}
_rate_map: dict[str, list[float]] = {}
_rate_limit: int = 30
_rate_window: float = 60.0


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:16]


async def semantic_cache_search(query: str, threshold: float = 0.95) -> Any | None:
    try:
        client = qdrant_client_manager.client
        emb = await embedding_client_manager.client.aembed_query(query)
        result = await client.query_points(
            collection_name=CACHE_COLLECTION,
            query=emb,
            limit=1,
            score_threshold=threshold,
        )
        if result.points:
            return result.points[0].payload.get("result")
    except Exception:
        pass
    return None


async def semantic_cache_save(query: str, result: Any):
    try:
        client = qdrant_client_manager.client
        emb = await embedding_client_manager.client.aembed_query(query)
        from qdrant_client.models import PointStruct
        pid = _query_hash(query)
        await client.upsert(
            collection_name=CACHE_COLLECTION,
            points=[PointStruct(id=pid, vector=emb, payload={"query": query, "result": result})],
        )
    except Exception:
        pass


async def ensure_cache_collection():
    try:
        client = qdrant_client_manager.client
        from qdrant_client.models import VectorParams, Distance
        if not await client.collection_exists(CACHE_COLLECTION):
            await client.create_collection(
                collection_name=CACHE_COLLECTION,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )
    except Exception:
        pass


def exact_cache_get(query: str) -> Any | None:
    h = _query_hash(query)
    entry = _cache.get(h)
    if entry and entry["exp"] > time.time():
        return entry["result"]
    return None


def exact_cache_set(query: str, result: Any, ttl: int = 300):
    h = _query_hash(query)
    _cache[h] = {"result": result, "exp": time.time() + ttl}


def check_rate_limit(key: str = "default") -> bool:
    now = time.time()
    if key not in _rate_map:
        _rate_map[key] = []
    _rate_map[key] = [t for t in _rate_map[key] if now - t < _rate_window]
    if len(_rate_map[key]) >= _rate_limit:
        return False
    _rate_map[key].append(now)
    return True
