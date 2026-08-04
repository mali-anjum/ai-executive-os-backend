"""Preflight: verify Postgres and Redis before starting uvicorn/celery."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `pnpm run db:check` from backend/ (same layout as uvicorn).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import create_engine, text

from app.core.db_connect import _is_supabase_pooler, resolve_ipv4, sync_connect_args


def main() -> int:
    from app.core.config import settings

    sync_url = settings.database_url.replace("+asyncpg", "")
    host_display = settings.database_url.split("@")[-1]
    parsed_host = host_display.split(":")[0].split("/")[0]
    use_pooler = _is_supabase_pooler(parsed_host)
    if use_pooler:
        print(f"Checking Postgres… {host_display}", flush=True)
    else:
        ipv4 = resolve_ipv4(parsed_host)
        if ipv4:
            print(f"Checking Postgres… {host_display} (using IPv4 {ipv4})", flush=True)
        else:
            print("Checking Postgres…", host_display, flush=True)
    try:
        engine = create_engine(
            sync_url,
            pool_pre_ping=True,
            connect_args=sync_connect_args(sync_url),
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        err = str(exc)
        print("\nPostgres check failed:", exc, file=sys.stderr)
        if "Network is unreachable" in err and "2600:" in err:
            print(
                "\nLikely cause: your network cannot reach Supabase over IPv6.",
                file=sys.stderr,
            )
            print(
                "For laptop prod testing, use local Docker DB instead:",
                file=sys.stderr,
            )
            print(
                "  cp .env.production.local.example .env.production.local",
                file=sys.stderr,
            )
            print(
                "  (copy SUPABASE_* / ENCRYPTION_KEY / GEMINI_* from .env.production)",
                file=sys.stderr,
            )
            print("  pnpm run deps:docker:all && pnpm run dev:prod:local", file=sys.stderr)
            print(
                "Or fix remote URL: Supabase Dashboard → Database → Session pooler URI (port 6543).",
                file=sys.stderr,
            )
        elif "password authentication failed" in err:
            print(
                "\nLikely cause: wrong database password or wrong postgres.<project-ref> user.",
                file=sys.stderr,
            )
            print(
                "  Run: pnpm run verify:supabase  (refs must match)",
                file=sys.stderr,
            )
            print(
                "  Supabase → Connect → Session pooler → copy URI → reset DB password if needed.",
                file=sys.stderr,
            )
        elif "Name or service not known" in err or "could not translate host" in err:
            print(
                "\nLikely cause: wrong DATABASE_URL host or no internet/DNS.",
                file=sys.stderr,
            )
            print(
                "Use Session pooler URI from Supabase Dashboard — see docs/SUPABASE_REMOTE_DATABASE.md",
                file=sys.stderr,
            )
        else:
            print(
                "\nFix: pnpm run deps:docker (local) or pnpm run dev:prod:local — see docs/DEV_VS_PRODUCTION.md",
                file=sys.stderr,
            )
        return 1

    print("Checking Redis…", settings.redis_url, flush=True)
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=3)
        client.ping()
    except Exception as exc:
        print("\nRedis check failed:", exc, file=sys.stderr)
        print("\nFix: pnpm run deps:docker  or set REDIS_URL in backend/.env", file=sys.stderr)
        return 1

    print("Postgres and Redis OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
