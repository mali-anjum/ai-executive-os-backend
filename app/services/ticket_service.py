"""
Ticket persistence — CRUD against Postgres tickets table.

Slack uniqueness: (org_id, slack_channel_id, slack_message_ts). IntegrityError
handler covers Celery races; list_tickets feeds GET /tickets for the Tasks UI.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db.tables import Ticket


class TicketService:
    """Org-scoped ticket rows; no Slack or LLM logic here."""

    async def list_tickets(
        self,
        db: AsyncSession,
        org_id: uuid.UUID | None = None,
        *,
        department: str | None = None,
        limit: int = 100,
    ) -> list[Ticket]:
        stmt = (
            select(Ticket)
            .order_by(Ticket.created_at.desc())
            .limit(limit)
            .options(selectinload(Ticket.assignee))
        )
        if org_id is not None:
            stmt = stmt.where(Ticket.org_id == org_id)
        if department:
            stmt = stmt.where(Ticket.department == department)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_ticket(self, db: AsyncSession, ticket_id: uuid.UUID) -> Ticket | None:
        result = await db.execute(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.assignee))
        )
        return result.scalar_one_or_none()

    async def find_by_slack_message(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        *,
        slack_channel_id: str | None,
        slack_message_ts: str | None,
    ) -> Ticket | None:
        if not slack_channel_id or not slack_message_ts:
            return None
        result = await db.execute(
            select(Ticket)
            .where(
                Ticket.org_id == org_id,
                Ticket.slack_channel_id == slack_channel_id,
                Ticket.slack_message_ts == slack_message_ts,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def approve_ticket(
        self,
        db: AsyncSession,
        ticket_id: uuid.UUID,
        *,
        org_id: uuid.UUID,
        approved_by_id: uuid.UUID,
        external_ticket_id: str | None = None,
    ) -> Ticket | None:
        ticket = await self.get_ticket(db, ticket_id)
        if not ticket or ticket.org_id != org_id:
            return None
        if ticket.approval_status not in ("pending", "pending_approval"):
            return ticket
        from datetime import datetime, timezone

        ticket.approval_status = "approved"
        ticket.approved_by_id = approved_by_id
        ticket.approved_at = datetime.now(timezone.utc)
        ticket.status = "assigned" if ticket.assignee_id else "open"
        if external_ticket_id:
            ticket.external_ticket_id = external_ticket_id
        await db.commit()
        await db.refresh(ticket)
        return ticket

    async def reject_ticket(
        self,
        db: AsyncSession,
        ticket_id: uuid.UUID,
        *,
        org_id: uuid.UUID,
        rejected_by_id: uuid.UUID,
    ) -> Ticket | None:
        ticket = await self.get_ticket(db, ticket_id)
        if not ticket or ticket.org_id != org_id:
            return None
        from datetime import datetime, timezone

        ticket.approval_status = "rejected"
        ticket.approved_by_id = rejected_by_id
        ticket.approved_at = datetime.now(timezone.utc)
        ticket.status = "closed"
        await db.commit()
        await db.refresh(ticket)
        return ticket

    async def create_ticket_record(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        source: str,
        raw_payload: dict[str, Any],
        intent: str,
        priority: int,
        summary: str,
        department: str,
        assignee_id: uuid.UUID | None,
        slack_channel_id: str | None = None,
        slack_message_ts: str | None = None,
        requires_approval: bool = False,
        approval_status: str = "auto_approved",
        status: str | None = None,
    ) -> Ticket:
        if slack_channel_id and slack_message_ts:
            existing = await self.find_by_slack_message(
                db,
                org_id,
                slack_channel_id=slack_channel_id,
                slack_message_ts=slack_message_ts,
            )
            if existing:
                return existing

        resolved_status = status
        if resolved_status is None:
            if requires_approval:
                resolved_status = "pending_approval"
            else:
                resolved_status = "assigned" if assignee_id else "open"

        ticket = Ticket(
            org_id=org_id,
            source=source,
            title=(summary[:255] if summary else None),
            raw_payload=raw_payload,
            intent=intent,
            priority=priority,
            summary=summary,
            department=department,
            assignee_id=assignee_id,
            status=resolved_status,
            requires_approval=requires_approval,
            approval_status=approval_status,
            slack_channel_id=slack_channel_id,
            slack_message_ts=slack_message_ts,
        )
        db.add(ticket)
        try:
            await db.commit()
            await db.refresh(ticket)
            return ticket
        except IntegrityError:
            await db.rollback()
            if slack_channel_id and slack_message_ts:
                existing = await self.find_by_slack_message(
                    db,
                    org_id,
                    slack_channel_id=slack_channel_id,
                    slack_message_ts=slack_message_ts,
                )
                if existing:
                    return existing
            raise
