"""Fernet encrypt/decrypt for stored secrets — requires ENCRYPTION_KEY in production."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    raw = settings.encryption_key or "dev-only-change-me-in-production-32b!"
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
    return Fernet(key)


def encrypt_value(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_value(cipher: str) -> str:
    if not cipher:
        return ""
    return _fernet().decrypt(cipher.encode()).decode()
