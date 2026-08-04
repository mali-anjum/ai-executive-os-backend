"""Escalate low-confidence RAG answers to human support tickets."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ticket_service import TicketService


class EscalationService:
    """Creates an org-scoped ticket when the Knowledge Agent cannot answer confidently."""

    def __init__(self) -> None:
        self.tickets = TicketService()

    async def escalate_query(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID | None,
        query: str,
        confidence: float,
        answer_preview: str,
    ) -> uuid.UUID:
        summary = (
            f"[Escalation] Low confidence ({confidence:.0%}): "
            f"{query[:160]}"
        )
        ticket = await self.tickets.create_ticket_record(
            db,
            org_id=org_id,
            source="api",
            raw_payload={
                "type": "rag_escalation",
                "query": query,
                "confidence": confidence,
                "answer_preview": answer_preview[:500],
                "user_id": str(user_id) if user_id else None,
            },
            intent="escalation",
            priority=3,
            summary=summary,
            department="support",
            assignee_id=None,
            requires_approval=False,
            approval_status="auto_approved",
            status="open",
        )
        return ticket.id
