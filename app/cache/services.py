import hashlib
import json
import time
from typing import Any

from app.clients.qdrant_client_manager import qdrant_client_manager
from app.clients.embedding_client_manager import embedding_client_manager
from app.conf.app_config import app_config
from app.core.log import logger

CACHE_COLLECTION = app_config.qdrant.cache_collection
_cache: dict[str, dict] = {}
_rate_map: dict[str, list[float]] = {}
_rate_limit: int = app_config.auth.rate_limit_per_minute
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
    except Exception as e:
        logger.warning(f"Cache search failed: {e}")
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
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


async def ensure_cache_collection():
    try:
        client = qdrant_client_manager.client
        from qdrant_client.models import VectorParams, Distance
        if not await client.collection_exists(CACHE_COLLECTION):
            await client.create_collection(
                collection_name=CACHE_COLLECTION,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )
    except Exception as e:
        logger.warning(f"Cache collection init failed: {e}")


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
