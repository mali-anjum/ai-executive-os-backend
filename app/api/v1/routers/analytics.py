"""Admin analytics dashboard — aggregated org metrics (read-only, admin role)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.feature_flags import flags
from sqlalchemy import select

from app.core.security import AuthContext, require_admin, require_leadership, tenant_org_id
from app.models.db.tables import User
from app.models.http.schemas import AnalyticsDashboard, ExecutiveSummary
from app.services.analytics_service import AnalyticsService
from app.services.executive_summary_service import ExecutiveSummaryService

router = APIRouter()


async def _department_scope(
    db: AsyncSession, auth: AuthContext
) -> str | None:
    if auth.role != "manager":
        return None
    result = await db.execute(select(User.department).where(User.id == auth.user_id))
    return result.scalar_one_or_none()


@router.get("/analytics/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_leadership),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.ANALYTICS_DASHBOARD_ENABLED:
        raise HTTPException(status_code=404, detail="Analytics dashboard is not enabled")

    service = AnalyticsService()
    metrics = await service.get_dashboard_metrics(db, org_id or auth.org_id)
    return AnalyticsDashboard(**metrics)


@router.get("/analytics/executive-summary", response_model=ExecutiveSummary)
async def get_executive_summary(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_leadership),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.ANALYTICS_DASHBOARD_ENABLED:
        raise HTTPException(status_code=404, detail="Analytics dashboard is not enabled")

    department = await _department_scope(db, auth)
    service = ExecutiveSummaryService()
    summary = await service.get_summary(
        db, org_id or auth.org_id, department=department
    )
    return ExecutiveSummary(**summary)
