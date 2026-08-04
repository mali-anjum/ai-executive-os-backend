#!/usr/bin/env python3
"""Process a pending document synchronously (bypasses Celery). Usage:

  ENV_FILE=.env.production .venv/bin/python scripts/reprocess_document.py <document-uuid>
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.services.document_service import DocumentService  # noqa: E402


async def main(doc_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        service = DocumentService()
        await service.process_document(db, doc_id)
    print(f"Processed document {doc_id}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: reprocess_document.py <document-uuid>", file=sys.stderr)
        raise SystemExit(2)
    asyncio.run(main(uuid.UUID(sys.argv[1])))
