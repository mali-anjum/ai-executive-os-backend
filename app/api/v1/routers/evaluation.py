"""RAG evaluation dashboard — accuracy, escalation, feedback."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.feature_flags import flags
from app.core.security import AuthContext, get_current_user, require_leadership, tenant_org_id
from app.models.http.schemas import (
    EvaluationMetrics,
    HarnessRunResponse,
    QueryFeedbackRequest,
    UnansweredQuestionsReport,
)
from app.services.evaluation_harness_service import EvaluationHarnessService
from app.services.evaluation_service import EvaluationService

router = APIRouter()


@router.get("/evaluation/metrics", response_model=EvaluationMetrics)
async def get_evaluation_metrics(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_leadership),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.EVALUATION_DASHBOARD_ENABLED:
        raise HTTPException(status_code=404, detail="Evaluation dashboard is not enabled")
    service = EvaluationService()
    data = await service.get_metrics(db, org_id or auth.org_id)
    return EvaluationMetrics(**data)


@router.get("/evaluation/unanswered", response_model=UnansweredQuestionsReport)
async def get_unanswered_report(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_leadership),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.EVALUATION_DASHBOARD_ENABLED:
        raise HTTPException(status_code=404, detail="Evaluation dashboard is not enabled")
    service = EvaluationService()
    data = await service.get_unanswered_report(db, org_id or auth.org_id)
    return UnansweredQuestionsReport(**data)


@router.get("/evaluation/harness/cases")
async def list_harness_cases(
    auth: AuthContext = Depends(require_leadership),
):
    if not flags.EVALUATION_DASHBOARD_ENABLED:
        raise HTTPException(status_code=404, detail="Evaluation dashboard is not enabled")
    service = EvaluationHarnessService()
    return {"cases": service.list_cases()}


@router.post("/evaluation/harness/run", response_model=HarnessRunResponse)
async def run_evaluation_harness(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_leadership),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.EVALUATION_DASHBOARD_ENABLED:
        raise HTTPException(status_code=404, detail="Evaluation dashboard is not enabled")
    service = EvaluationHarnessService()
    data = await service.run_harness(
        db,
        org_id or auth.org_id,
        user_role=auth.role,
        user_department=None,
    )
    return HarnessRunResponse(**data)


@router.post("/queries/{query_id}/feedback", status_code=204)
async def submit_query_feedback(
    query_id: uuid.UUID,
    body: QueryFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.EVALUATION_DASHBOARD_ENABLED:
        raise HTTPException(status_code=404, detail="Evaluation dashboard is not enabled")
    service = EvaluationService()
    ok = await service.set_feedback(
        db, query_id, org_id or auth.org_id, body.feedback
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Query not found")
