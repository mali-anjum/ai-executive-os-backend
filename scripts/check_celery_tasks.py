#!/usr/bin/env python3
"""Exit 0 when Celery registers process_document + process_slack_event."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.tasks.celery_app import celery_app  # noqa: E402

REQUIRED = ("process_document", "process_slack_event")


def main() -> int:
    missing = [name for name in REQUIRED if name not in celery_app.tasks]
    if missing:
        print("Celery task registration FAILED. Missing:", ", ".join(missing))
        print("Restart the worker after changing app/tasks/celery_app.py:")
        print("  cd backend && pnpm run worker:prod")
        return 1
    print("Celery tasks OK:", ", ".join(REQUIRED))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
