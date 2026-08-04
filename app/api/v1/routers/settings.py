"""Org integration settings — Jira, Notion, Google Drive credentials."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.feature_flags import flags
from app.core.security import AuthContext, require_admin, tenant_org_id
from app.models.http.schemas import IntegrationConfigRequest
from app.services.integration_settings_service import IntegrationSettingsService

router = APIRouter()


@router.get("/settings/integrations")
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.INTEGRATIONS_SETTINGS_ENABLED:
        raise HTTPException(status_code=404, detail="Integrations settings are not enabled")
    service = IntegrationSettingsService()
    providers = await service.list_providers(db, org_id or auth.org_id)
    return {"providers": providers}


@router.put("/settings/integrations", status_code=204)
async def upsert_integration(
    body: IntegrationConfigRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.INTEGRATIONS_SETTINGS_ENABLED:
        raise HTTPException(status_code=404, detail="Integrations settings are not enabled")
    allowed = {"jira", "notion", "google_drive"}
    if body.provider not in allowed:
        raise HTTPException(status_code=400, detail=f"Provider must be one of {sorted(allowed)}")
    service = IntegrationSettingsService()
    await service.upsert_config(db, org_id or auth.org_id, body.provider, body.config)
