"""Print APP_ENV and run startup validation (development or production rules)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.startup import validate_environment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate backend environment")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Validate production rules (else use rules for current APP_ENV)",
    )
    args = parser.parse_args()

    prod_mode = args.production or settings.app_env.lower() in (
        "production",
        "prod",
    )
    label = "production" if prod_mode else "development"

    print(f"APP_ENV={settings.app_env!r} (validating as {label})")
    print(f"DATABASE_URL host: {settings.database_url.split('@')[-1]}")
    print(f"REDIS_URL: {settings.redis_url.split('@')[-1] if '@' in settings.redis_url else settings.redis_url}")

    errors = validate_environment(production=prod_mode)
    if errors:
        print("\nValidation FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("\nValidation passed.")
    if prod_mode:
        print("Tip: start with pnpm run dev, sign in via Supabase, test chat (no X-Org-Id headers).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
