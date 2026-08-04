"""Document background task wiring."""

from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.tasks import document_tasks
from app.tasks.document_tasks import process_document_task


def test_task_exposes_expected_celery_name():
    assert process_document_task.name == "process_document"


def test_process_document_task_invokes_service(monkeypatch):
    doc_id = uuid.uuid4()
    mock_process = AsyncMock()
    monkeypatch.setattr(
        document_tasks.DocumentService,
        "process_document",
        mock_process,
    )

    class FakeSession:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(document_tasks, "CeleryAsyncSessionLocal", lambda: FakeSession())

    result = process_document_task(str(doc_id))

    assert result == str(doc_id)
    mock_process.assert_awaited_once()
    call_args = mock_process.await_args
    assert call_args.args[1] == doc_id
