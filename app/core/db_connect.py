"""Supabase-friendly connect_args — SSL, IPv4 fallback, pooler hostname rules."""

from __future__ import annotations
import ssl

import socket
from urllib.parse import urlparse


def _should_use_remote_ssl(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.lower()
    return host.endswith(".supabase.co") or "pooler.supabase.com" in host


def resolve_ipv4(hostname: str) -> str | None:
    """Return first IPv4 address for hostname, or None if resolution fails."""
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
    except socket.gaierror:
        return None
    if not infos:
        return None
    # sockaddr[0] is typed as str | int across address families; AF_INET host is str.
    host = infos[0][4][0]
    return str(host)


def _is_supabase_pooler(hostname: str) -> bool:
    return "pooler.supabase.com" in hostname.lower()


def sync_connect_args(database_url: str) -> dict:
    """Extra connect_args for psycopg2 (Alembic, db:check)."""
    parsed = urlparse(database_url.replace("+asyncpg", ""))
    hostname = parsed.hostname
    if not hostname or hostname in ("127.0.0.1", "localhost"):
        return {}

    args: dict = {}
    if _should_use_remote_ssl(hostname):
        args["sslmode"] = "require"

    # Session pooler must connect by hostname so user postgres.<ref> is honored.
    # hostaddr-only breaks auth (server reports user "postgres").
    if not _is_supabase_pooler(hostname):
        ipv4 = resolve_ipv4(hostname)
        if ipv4:
            args["hostaddr"] = ipv4

    return args

def async_connect_args(database_url: str) -> dict:
    """Extra connect_args for asyncpg (FastAPI runtime)."""
    # --- Intercept and clean up query parameters ---
    if "sslmode=" in database_url:
        from app.core.config import settings
        clean_url = database_url.split("?", 1)[0]
        if "ssl=true" in database_url.lower() or "sslmode=require" in database_url.lower():
            clean_url += "?ssl=true"
        settings.database_url = clean_url
        database_url = clean_url
    # -----------------------------------------------

    parsed = urlparse(database_url)
    hostname = parsed.hostname
    if not hostname or hostname in ("127.0.0.1", "localhost"):
        return {}

    args: dict = {}
    
    # --- FIX TRANSACTION POOLER CACHE ERROR ---
    # Disable prepared statement caching if utilizing a Supabase pooling architecture
    if _is_supabase_pooler(hostname):
        args["statement_cache_size"] = 0
    # -------------------------------------------

    if _should_use_remote_ssl(hostname):
        # Create an SSL context that allows self-signed certificate chains from the pooler
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        args["ssl"] = ctx

    if not _is_supabase_pooler(hostname):
        ipv4 = resolve_ipv4(hostname)
        if ipv4:
            args["host"] = ipv4
            args["server_hostname"] = hostname

    return args