"""
Tasks UI data source — ticket feed and human approval before Jira.

Written by ProjectAgent (Slack path); polled by frontend useTickets with adaptive
intervals. Gated by PROJECT_AGENT_ENABLED.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db.tables import User
from app.core.feature_flags import flags
from app.core.security import (
    AuthContext,
    get_current_user,
    require_leadership,
    tenant_org_id,
)
from app.models.http.schemas import TicketResponse
from app.models.internal.coerce import as_ticket_source, as_ticket_status
from app.services.integration_settings_service import IntegrationSettingsService
from app.services.jira_service import JiraService
from app.services.notification_service import NotificationService
from app.services.ticket_service import TicketService

router = APIRouter()


@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.PROJECT_AGENT_ENABLED:
        raise HTTPException(status_code=404, detail="Project agent is not enabled")

    department: str | None = None
    if auth.role == "manager":
        dept_result = await db.execute(
            select(User.department).where(User.id == auth.user_id)
        )
        department = dept_result.scalar_one_or_none()

    service = TicketService()
    tickets = await service.list_tickets(
        db,
        org_id=org_id or auth.org_id,
        department=department,
    )
    return [
        TicketResponse(
            id=t.id,
            source=as_ticket_source(t.source),
            title=t.title or t.summary,
            intent=t.intent,
            priority=t.priority,
            summary=t.summary,
            department=t.department,
            status=as_ticket_status(t.status),
            assignee_email=t.assignee.email if t.assignee else None,
            assignee_name=t.assignee.full_name if t.assignee else None,
            assignee_id=t.assignee_id,
            slack_channel_id=t.slack_channel_id,
            requires_approval=t.requires_approval,
            approval_status=t.approval_status,
            external_ticket_id=t.external_ticket_id,
            due_at=t.due_at,
            created_at=t.created_at,
        )
        for t in tickets
    ]


@router.post("/tickets/{ticket_id}/approve", response_model=TicketResponse)
async def approve_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_leadership),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.TICKET_APPROVAL_ENABLED:
        raise HTTPException(status_code=404, detail="Ticket approval is not enabled")

    service = TicketService()
    resolved_org = org_id or auth.org_id
    ticket = await service.get_ticket(db, ticket_id)
    if not ticket or ticket.org_id != resolved_org:
        raise HTTPException(status_code=404, detail="Ticket not found")

    external_id: str | None = None
    if flags.JIRA_INTEGRATION_ENABLED:
        settings_svc = IntegrationSettingsService()
        jira_cfg = await settings_svc.get_config(db, resolved_org, "jira")
        if jira_cfg:
            jira = JiraService()
            external_id = await jira.create_issue(
                site_url=jira_cfg.get("site_url", ""),
                email=jira_cfg.get("email", ""),
                api_token=jira_cfg.get("api_token", ""),
                ticket=ticket,
                project_key=jira_cfg.get("project_key", "OPS"),
            )

    approved = await service.approve_ticket(
        db,
        ticket_id,
        org_id=resolved_org,
        approved_by_id=auth.user_id,
        external_ticket_id=external_id,
    )
    if not approved:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if approved.assignee:
        await NotificationService().notify_slack_dm(approved.assignee, approved)

    return TicketResponse(
        id=approved.id,
        source=as_ticket_source(approved.source),
        title=approved.title or approved.summary,
        intent=approved.intent,
        priority=approved.priority,
        summary=approved.summary,
        department=approved.department,
        status=as_ticket_status(approved.status),
        assignee_email=approved.assignee.email if approved.assignee else None,
        assignee_name=approved.assignee.full_name if approved.assignee else None,
        assignee_id=approved.assignee_id,
        slack_channel_id=approved.slack_channel_id,
        requires_approval=approved.requires_approval,
        approval_status=approved.approval_status,
        external_ticket_id=approved.external_ticket_id,
        due_at=approved.due_at,
        created_at=approved.created_at,
    )


@router.post("/tickets/{ticket_id}/reject", response_model=TicketResponse)
async def reject_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_leadership),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.TICKET_APPROVAL_ENABLED:
        raise HTTPException(status_code=404, detail="Ticket approval is not enabled")

    service = TicketService()
    resolved_org = org_id or auth.org_id
    rejected = await service.reject_ticket(
        db,
        ticket_id,
        org_id=resolved_org,
        rejected_by_id=auth.user_id,
    )
    if not rejected:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketResponse(
        id=rejected.id,
        source=as_ticket_source(rejected.source),
        title=rejected.title or rejected.summary,
        intent=rejected.intent,
        priority=rejected.priority,
        summary=rejected.summary,
        department=rejected.department,
        status=as_ticket_status(rejected.status),
        assignee_email=rejected.assignee.email if rejected.assignee else None,
        assignee_name=rejected.assignee.full_name if rejected.assignee else None,
        assignee_id=rejected.assignee_id,
        slack_channel_id=rejected.slack_channel_id,
        requires_approval=rejected.requires_approval,
        approval_status=rejected.approval_status,
        external_ticket_id=rejected.external_ticket_id,
        due_at=rejected.due_at,
        created_at=rejected.created_at,
    )
