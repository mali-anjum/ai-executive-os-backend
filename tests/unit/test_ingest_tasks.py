"""Ingest endpoint must queue process_document for Celery workers."""

from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth_context import AuthContext
from app.core.security import require_admin, tenant_org_id
from app.main import app


@pytest.mark.asyncio
async def test_ingest_queues_process_document_task():
    doc_id = uuid.uuid4()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    auth = AuthContext(user_id=user_id, org_id=org_id, role="admin", email="a@b.co")

    fake_doc = MagicMock()
    fake_doc.id = doc_id
    fake_doc.status = "pending"

    async def _admin():
        return auth

    async def _org():
        return org_id

    app.dependency_overrides[require_admin] = _admin
    app.dependency_overrides[tenant_org_id] = _org

    try:
        with (
            patch(
                "app.api.v1.routers.ingest.DocumentService.save_upload",
                new_callable=AsyncMock,
                return_value=fake_doc,
            ) as save_mock,
            patch(
                "app.api.v1.routers.ingest.process_document.delay",
            ) as delay_mock,
            patch(
                "app.api.v1.routers.ingest.flags",
                MagicMock(DOCUMENT_UPLOAD_ENABLED=True),
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                files = {"file": ("test.txt", b"hello world", "text/plain")}
                res = await ac.post("/api/v1/ingest", files=files)

        assert res.status_code == 202
        save_mock.assert_awaited_once()
        delay_mock.assert_called_once_with(str(doc_id))
    finally:
        app.dependency_overrides.clear()
