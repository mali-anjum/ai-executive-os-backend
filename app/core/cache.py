"""
Redis cache for Knowledge Agent answers (RAG path only).

Keyed by query + org_id; gated by RAG_CACHE_ENABLED. Separate from Slack dedupe
keys and from LlmClassifyCircuit — reduces repeat LLM cost on identical questions.
"""

import hashlib
import json
import logging
from typing import Any

from app.core.config import settings
from app.core.redis_client import create_async_redis

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 3600


class QueryCacheService:
    """Read-through cache for /query responses; safe no-op when Redis is unavailable."""

    def __init__(self) -> None:
        self._redis = None

    async def _client(self):
        if not settings.redis_url:
            return None
        if self._redis is None:
            self._redis = create_async_redis(settings.redis_url)
        return self._redis

    @staticmethod
    def cache_key(query_text: str, org_id: str | None) -> str:
        normalized = query_text.strip().lower()
        raw = f"{normalized}:{org_id or 'global'}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return f"rag:answer:{digest}"

    async def get_cached_answer(
        self, query_text: str, org_id: str | None
    ) -> dict[str, Any] | None:
        client = await self._client()
        if not client:
            return None
        try:
            raw = await client.get(self.cache_key(query_text, org_id))
            if not raw:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("cache_get_failed: %s", exc)
            return None

    async def set_cached_answer(
        self,
        query_text: str,
        org_id: str | None,
        payload: dict[str, Any],
        *,
        ttl_seconds: int = _CACHE_TTL_SECONDS,
    ) -> None:
        client = await self._client()
        if not client:
            return
        try:
            await client.setex(
                self.cache_key(query_text, org_id),
                ttl_seconds,
                json.dumps(payload),
            )
        except Exception as exc:
            logger.warning("cache_set_failed: %s", exc)
