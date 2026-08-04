"""
Per-tenant HTTP rate limits (slowapi).

Applied on expensive routes (query stream, ingest). Keys by user/org header in dev
or JWT-derived identity — protects LLM and embedding cost from abuse.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def user_rate_limit_key(request: Request) -> str:
    user_id = request.headers.get("X-User-Id")
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


def org_rate_limit_key(request: Request) -> str:
    org_id = request.headers.get("X-Org-Id")
    if org_id:
        return f"org:{org_id}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=user_rate_limit_key)
