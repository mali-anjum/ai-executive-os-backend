"""Decode Bearer tokens — JWKS first, legacy HS256 fallback for old projects."""

from __future__ import annotations

import logging
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.core.config import settings

logger = logging.getLogger(__name__)

JWKS_ALGORITHMS = ("RS256", "ES256", "EdDSA")
LEGACY_ALGORITHM = "HS256"
AUDIENCE = "authenticated"


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient | None:
    url = settings.supabase_jwks_url
    if not url:
        return None
    return PyJWKClient(url, cache_keys=True)


def clear_jwks_client_cache() -> None:
    _jwks_client.cache_clear()


def decode_supabase_access_token(token: str) -> dict:
    """Verify a Supabase Auth access token and return its claims."""
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "")

    if alg == LEGACY_ALGORITHM:
        return _decode_legacy_hs256(token)

    if settings.supabase_jwks_url:
        return _decode_jwks(token)

    if settings.supabase_jwt_secret:
        return _decode_legacy_hs256(token)

    raise jwt.InvalidTokenError(
        "Set SUPABASE_URL for JWKS verification (asymmetric signing keys), "
        "or SUPABASE_JWT_SECRET only if the project still issues legacy HS256 tokens."
    )


def _decode_jwks(token: str) -> dict:
    client = _jwks_client()
    if client is None:
        raise jwt.InvalidTokenError("SUPABASE_URL is required for JWT verification")

    signing_key = client.get_signing_key_from_jwt(token)
    issuer = settings.supabase_jwt_issuer
    if not issuer:
        raise jwt.InvalidTokenError("SUPABASE_URL is required for JWT verification")

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=list(JWKS_ALGORITHMS),
        audience=AUDIENCE,
        issuer=issuer,
    )


def _decode_legacy_hs256(token: str) -> dict:
    if not settings.supabase_jwt_secret:
        raise jwt.InvalidTokenError(
            "Legacy HS256 token: set SUPABASE_JWT_SECRET temporarily, or enable "
            "asymmetric JWT signing keys in Supabase and set SUPABASE_URL for JWKS."
        )
    logger.warning(
        "Verifying Supabase JWT with legacy HS256 secret; prefer asymmetric signing keys + JWKS."
    )
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=[LEGACY_ALGORITHM],
        audience=AUDIENCE,
    )
