"""
AI Assistant API — sync and SSE streaming answers from KnowledgeAgent.

Auth + org scope required; rate-limited. This is the user-facing RAG path, separate
from Slack ticket ingestion (Project Agent).
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.knowledge_agent import KnowledgeAgent
from app.models.db.tables import QueryLog, User
from app.core.database import get_db
from app.models.http.responses import STANDARD_ERROR_RESPONSES
from app.core.feature_flags import flags
from app.core.security import AuthContext, get_current_user, tenant_org_id
from app.models.http.schemas import (
    QueryEscalateRequest,
    QueryEscalateResponse,
    QueryRequest,
    QueryResponse,
)
from app.services.escalation_service import EscalationService
from app.models.http.stream import StreamErrorEvent

router = APIRouter()
logger = logging.getLogger(__name__)


async def _load_user_department(db: AsyncSession, auth: AuthContext) -> str | None:
    result = await db.execute(select(User.department).where(User.id == auth.user_id))
    return result.scalar_one_or_none()


@router.post("/query", response_model=QueryResponse, responses=STANDARD_ERROR_RESPONSES)
async def query_knowledge(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.KNOWLEDGE_AGENT_ENABLED:
        raise HTTPException(status_code=404, detail="Knowledge agent is not enabled")

    agent = KnowledgeAgent()
    user = await _load_user_department(db, auth)
    return await agent.run(
        db,
        body.query,
        user_id=auth.user_id,
        org_id=org_id or auth.org_id,
        session_id=body.session_id,
        user_role=auth.role,
        user_department=user,
    )


@router.post("/query/stream", responses=STANDARD_ERROR_RESPONSES)
async def query_knowledge_stream(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.KNOWLEDGE_AGENT_ENABLED:
        raise HTTPException(status_code=404, detail="Knowledge agent is not enabled")

    agent = KnowledgeAgent()

    async def event_stream():
        try:
            user_dept = await _load_user_department(db, auth)
            async for line in agent.run_stream(
                db,
                body.query,
                user_id=auth.user_id,
                org_id=org_id or auth.org_id,
                session_id=body.session_id,
                user_role=auth.role,
                user_department=user_dept,
            ):
                yield f"data: {line}\n\n"
        except Exception:
            logger.exception("Knowledge stream failed")
            message = (
                "The assistant could not finish this response. "
                "If you use Gemini, wait a moment (rate limits) or set OPENAI_API_KEY."
            )
            err: StreamErrorEvent = {"type": "error", "message": message}
            yield f"data: {json.dumps(err)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/query/escalate", response_model=QueryEscalateResponse)
async def escalate_query_to_human(
    body: QueryEscalateRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.CONFIDENCE_ESCALATION_ENABLED:
        raise HTTPException(
            status_code=404, detail="Confidence escalation is not enabled"
        )

    resolved_org = org_id or auth.org_id
    confidence = body.confidence_score if body.confidence_score is not None else 0.0
    escalation = EscalationService()
    ticket_id = await escalation.escalate_query(
        db,
        org_id=resolved_org,
        user_id=auth.user_id,
        query=body.query,
        confidence=confidence,
        answer_preview=body.answer_preview or "",
    )

    if body.query_log_id:
        result = await db.execute(
            select(QueryLog).where(
                QueryLog.id == body.query_log_id,
                QueryLog.org_id == resolved_org,
            )
        )
        log = result.scalar_one_or_none()
        if log:
            log.escalated = True
            log.escalation_ticket_id = ticket_id
            await db.commit()

    return QueryEscalateResponse(
        escalated=True,
        escalation_ticket_id=ticket_id,
        message="Your question has been escalated to human support.",
    )
