"""
Celery bridge: uploaded document → chunk, embed, store in pgvector.

Triggered by POST /ingest (202). DocumentService does the work; worker updates
status so Knowledge page polling sees pending → ready.
"""

import asyncio
import uuid
from typing import cast

from celery.app.task import Task

from app.core.database import CeleryAsyncSessionLocal
from app.services.document_service import DocumentService
from app.tasks.celery_app import celery_app


def _run_async(coro):
    return asyncio.run(coro)


@celery_app.task(name="process_document")
def process_document_task(document_id: str) -> str:
    async def _process():
        async with CeleryAsyncSessionLocal() as db:
            service = DocumentService()
            await service.process_document(db, uuid.UUID(document_id))

    _run_async(_process())
    return document_id


process_document: Task = cast(Task, process_document_task)
