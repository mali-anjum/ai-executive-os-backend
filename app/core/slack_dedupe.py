"""
First line of defense against duplicate Slack tickets.

Slack retries the same event from multiple IPs; SET NX in Redis before enqueueing
Celery ensures only one process_slack_event task per event_id (or channel+ts).
DB unique index is the second line — see ticket_service + migration 005.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.redis_client import create_async_redis

logger = logging.getLogger(__name__)

_SLACK_DEDUPE_TTL_SECONDS = 60 * 60 * 24


class SlackEventDedupe:
    """Redis SET NX gate; claim() True = process this delivery, False = Slack retry."""

    def __init__(self) -> None:
        self._redis = None

    async def _client(self):
        url = settings.redis_url
        if not url:
            return None
        if self._redis is None:
            self._redis = create_async_redis(url)
        return self._redis

    async def claim(self, key: str, *, ttl_seconds: int = _SLACK_DEDUPE_TTL_SECONDS) -> bool:
        """
        Return True if this delivery should be processed (first time we see `key`).
        Return False if Slack retried the same event_id / channel+ts.
        """
        client = await self._client()
        if not client:
            return True
        redis_key = f"slack:dedupe:{key}"
        try:
            claimed = await client.set(redis_key, "1", nx=True, ex=ttl_seconds)
            return bool(claimed)
        except Exception as exc:
            logger.warning("slack_dedupe_failed: %s", exc)
            return True

    async def aclose(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


slack_event_dedupe = SlackEventDedupe()
