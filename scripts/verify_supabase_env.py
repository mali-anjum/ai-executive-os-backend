"""Check SUPABASE_URL, DATABASE_URL pooler user, and service-role JWT refer to the same project."""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _ref_from_supabase_url(url: str) -> str | None:
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith("/rest/v1"):
        cleaned = cleaned[: -len("/rest/v1")]
    m = re.search(r"https://([a-z0-9]+)\.supabase\.co", cleaned)
    return m.group(1) if m else None


def _ref_from_database_url(url: str) -> str | None:
    parsed = urlparse(url.replace("+asyncpg", ""))
    user = parsed.username or ""
    if user.startswith("postgres."):
        return user.removeprefix("postgres.")
    return None


def _ref_from_service_role_jwt(key: str) -> str | None:
    token = key.strip()
    if not token or token.count(".") < 2:
        return None
    try:
        payload_b64 = token.split(".")[1]
        padding = "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
        return payload.get("ref")
    except (json.JSONDecodeError, ValueError):
        return None


def main() -> int:
    from app.core.config import settings

    url_ref = _ref_from_supabase_url(settings.supabase_url)
    db_ref = _ref_from_database_url(settings.database_url)
    jwt_ref = _ref_from_service_role_jwt(settings.supabase_service_role_key)

    print("Supabase project ref alignment:")
    print(f"  SUPABASE_URL ref:           {url_ref or '(missing)'}")
    print(f"  DATABASE_URL user ref:      {db_ref or '(missing — need postgres.<ref> on pooler)'}")
    print(f"  SUPABASE_SERVICE_ROLE ref:  {jwt_ref or '(missing or invalid JWT)'}")

    errors: list[str] = []
    refs = {r for r in (url_ref, db_ref, jwt_ref) if r}
    if len(refs) > 1:
        errors.append(
            "Mismatched project refs — copy Session pooler URI, SUPABASE_URL, and "
            "service_role key from the SAME Supabase project (Dashboard → Settings → API)."
        )
    if db_ref and url_ref and db_ref != url_ref:
        errors.append(f"DATABASE_URL user postgres.{db_ref} does not match SUPABASE_URL ({url_ref}).")
    if jwt_ref and url_ref and jwt_ref != url_ref:
        errors.append(
            f"Service role key is for project '{jwt_ref}' but SUPABASE_URL is '{url_ref}'."
        )
    if not db_ref:
        errors.append(
            "Pooler DATABASE_URL must use user postgres.<project-ref>, not postgres alone."
        )
    if settings.supabase_url.rstrip("/").endswith("/rest/v1"):
        errors.append(
            "SUPABASE_URL must be project root (https://<ref>.supabase.co), not Data API /rest/v1/."
        )

    if errors:
        print("\nFAILED:")
        for e in errors:
            print(f"  - {e}")
        print("\nFix: Supabase → Connect → Session pooler → copy URI → update DATABASE_URL.")
        print("     Settings → API → service_role → update SUPABASE_SERVICE_ROLE_KEY.")
        print("     Database → Reset password if auth still fails.")
        return 1

    print("\nAll refs match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
