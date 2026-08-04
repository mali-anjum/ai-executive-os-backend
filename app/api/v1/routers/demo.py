"""One-click demo tenant seeding for client presentations."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.feature_flags import flags
from app.core.security import AuthContext, require_admin, tenant_org_id
from app.models.http.schemas import DemoSeedResponse
from app.services.demo_seed_service import DemoSeedService

router = APIRouter()


@router.post("/demo/seed", response_model=DemoSeedResponse)
async def seed_demo_tenant(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.DEMO_TENANT_ENABLED:
        raise HTTPException(status_code=404, detail="Demo tenant seeding is not enabled")

    service = DemoSeedService()
    result = await service.seed_org(
        db,
        org_id=org_id or auth.org_id,
        user_id=auth.user_id,
    )
    return DemoSeedResponse(**result)
