"""
Redis connection helper for FastAPI async code (not Celery).

Celery uses redis_url_for_celery with SSL in the URL; redis-py needs SSL as a kwarg.
Used by slack_dedupe and RAG query cache — same Upstash instance as the Celery broker.
"""

from __future__ import annotations

import ssl
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import redis.asyncio as aioredis


def _normalize_redis_url(url: str) -> tuple[str, dict]:
    """
    Celery accepts ssl_cert_reqs=CERT_NONE in the URL query string.
    redis-py expects ssl_cert_reqs=ssl.CERT_NONE as a connection kwarg instead.
    """
    if not url.startswith("rediss://"):
        return url, {}

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.pop("ssl_cert_reqs", None)
    clean_query = urlencode(query)
    clean_url = urlunparse(parsed._replace(query=clean_query))
    return clean_url, {"ssl_cert_reqs": ssl.CERT_NONE}


def create_async_redis(url: str) -> aioredis.Redis:
    clean_url, ssl_kwargs = _normalize_redis_url(url)
    return aioredis.from_url(
        clean_url,
        encoding="utf-8",
        decode_responses=True,
        **ssl_kwargs,
    )
