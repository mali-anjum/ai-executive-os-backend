"""Notion and Google Drive sync connectors."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.feature_flags import flags
from app.core.security import AuthContext, require_admin, tenant_org_id
from app.models.http.schemas import (
    ConnectorSyncResponse,
    GoogleDriveSyncRequest,
    IngestResponse,
    NotionSyncRequest,
)
from app.tasks.connector_tasks import resync_connectors_for_org_task
from app.models.internal.coerce import as_document_status
from app.services.connector_service import ConnectorService
from app.services.integration_settings_service import IntegrationSettingsService
from typing import cast
from celery import Task

router = APIRouter()


@router.get("/connectors/syncs", response_model=list[ConnectorSyncResponse])
async def list_connector_syncs(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.CONNECTOR_SYNC_ENABLED:
        raise HTTPException(status_code=404, detail="Connector sync is not enabled")
    connector = ConnectorService()
    return await connector.list_syncs(db, org_id or auth.org_id)


@router.post("/connectors/resync-all", status_code=202)
async def resync_all_connectors(
    auth: AuthContext = Depends(require_admin),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.CONNECTOR_SYNC_ENABLED:
        raise HTTPException(status_code=404, detail="Connector sync is not enabled")
    resolved = str(org_id or auth.org_id)
    cast(Task, resync_connectors_for_org_task).delay(resolved)
    return {"message": "Connector re-sync queued", "org_id": resolved}


@router.post("/connectors/notion/sync", response_model=IngestResponse, status_code=202)
async def sync_notion(
    body: NotionSyncRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.CONNECTOR_SYNC_ENABLED:
        raise HTTPException(status_code=404, detail="Connector sync is not enabled")
    settings_svc = IntegrationSettingsService()
    config = await settings_svc.get_config(db, org_id or auth.org_id, "notion")
    token = (config or {}).get("api_token")
    if not token:
        raise HTTPException(status_code=400, detail="Notion integration not configured")

    connector = ConnectorService()
    doc_id = await connector.sync_notion_page(
        db,
        org_id=org_id or auth.org_id,
        user_id=auth.user_id,
        page_id=body.page_id,
        api_token=token,
        allowed_departments=body.allowed_departments,
        allowed_roles=body.allowed_roles,
    )
    return IngestResponse(
        document_id=doc_id,
        status=as_document_status("pending"),
        message="Notion page queued for indexing",
    )


@router.post("/connectors/google-drive/sync", response_model=IngestResponse, status_code=202)
async def sync_google_drive(
    body: GoogleDriveSyncRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.CONNECTOR_SYNC_ENABLED:
        raise HTTPException(status_code=404, detail="Connector sync is not enabled")
    settings_svc = IntegrationSettingsService()
    config = await settings_svc.get_config(db, org_id or auth.org_id, "google_drive")
    token = (config or {}).get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail="Google Drive integration not configured")

    connector = ConnectorService()
    doc_id = await connector.sync_google_drive_file(
        db,
        org_id=org_id or auth.org_id,
        user_id=auth.user_id,
        file_id=body.file_id,
        access_token=token,
        allowed_departments=body.allowed_departments,
        allowed_roles=body.allowed_roles,
    )
    return IngestResponse(
        document_id=doc_id,
        status=as_document_status("pending"),
        message="Google Drive file queued for indexing",
    )
