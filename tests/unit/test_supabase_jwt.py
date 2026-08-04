import jwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core import supabase_jwt
from app.core.config import settings


def test_legacy_hs256_requires_secret(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", "")
    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    token = jwt.encode(
        {"sub": "user", "aud": "authenticated"},
        "secret",
        algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidTokenError, match="SUPABASE_JWT_SECRET"):
        supabase_jwt.decode_supabase_access_token(token)


def test_jwks_path_requires_supabase_url(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_jwt_secret", "")
    supabase_jwt.clear_jwks_client_cache()
    rsa_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    token = jwt.encode(
        {"sub": "user", "aud": "authenticated"},
        rsa_key,
        algorithm="RS256",
    )
    with pytest.raises(jwt.InvalidTokenError, match="SUPABASE_URL"):
        supabase_jwt.decode_supabase_access_token(token)


def test_legacy_hs256_decodes_with_secret(monkeypatch):
    secret = "test-legacy-secret"
    monkeypatch.setattr(settings, "supabase_jwt_secret", secret)
    monkeypatch.setattr(settings, "supabase_url", "")
    token = jwt.encode(
        {"sub": "abc", "aud": "authenticated", "email": "a@b.co"},
        secret,
        algorithm="HS256",
    )
    payload = supabase_jwt.decode_supabase_access_token(token)
    assert payload["sub"] == "abc"
    assert payload["email"] == "a@b.co"
