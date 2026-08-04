#!/usr/bin/env python3
"""Run from backend/: .venv/bin/python scripts/verify_imports.py"""

import importlib
import sys
from pathlib import Path

# Allow `import app` when run from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PACKAGES = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic_settings",
    "sqlalchemy",
    "asyncpg",
    "slowapi",
    "sentry_sdk",
    "openai",
    "langgraph",
    "celery",
    "redis",
    "cohere",
    "groq",
    "anthropic",
    "httpx",
    "cryptography",
    "pgvector",
    "jwt",
    "fitz",
    "docx",
    "tiktoken",
    "pytest",
]

SPECIAL = [("google.genai", "google.genai")]


def main() -> int:
    failed: list[str] = []
    for name in PACKAGES:
        try:
            importlib.import_module(name)
        except ImportError as e:
            failed.append(f"{name}: {e}")
    for label, mod in SPECIAL:
        try:
            importlib.import_module(mod)
        except ImportError as e:
            failed.append(f"{label}: {e}")
    try:
        importlib.import_module("app.main")
    except ImportError as e:
        failed.append(f"app.main: {e}")

    if failed:
        print("FAILED imports:")
        for line in failed:
            print(" ", line)
        return 1
    print(f"OK — {len(PACKAGES) + len(SPECIAL) + 1} modules imported")
    return 0


if __name__ == "__main__":
    sys.exit(main())
