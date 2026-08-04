"""Executive KPI summary — ROI metrics for admins and managers."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.tables import Document, QueryLog, Ticket
from app.models.internal.domain import TopQuestionRow

# Industry average: 25 minutes per manual knowledge lookup.
_MINUTES_SAVED_PER_AUTOMATED_QUERY = 25


class ExecutiveSummaryService:
    async def get_summary(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        *,
        department: str | None = None,
    ) -> dict:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Single aggregate query over QueryLog — computes total, today, escalated,
        # and low-confidence counts in one round-trip instead of four.
        agg_row = (
            await db.execute(
                select(
                    func.count(QueryLog.id).label("total"),
                    func.count(
                        case((QueryLog.created_at >= today_start, 1))
                    ).label("today"),
                    func.count(
                        case((QueryLog.escalated.is_(True), 1))
                    ).label("escalated"),
                    func.count(
                        case(
                            (
                                QueryLog.confidence_score.isnot(None)
                                & (QueryLog.confidence_score < 0.45)
                                & (QueryLog.escalated.is_(False)),
                                1,
                            )
                        )
                    ).label("low_conf"),
                ).where(QueryLog.org_id == org_id)
            )
        ).one()

        total_queries = agg_row.total or 0
        queries_today = agg_row.today or 0
        escalated_queries = agg_row.escalated or 0
        low_confidence_unanswered = agg_row.low_conf or 0

        # Documents + open tickets + knowledge gaps in parallel (independent
        # tables, safe to interleave on the same session since they're separate
        # statements). This cuts 3 sequential round-trips to 1 parallel batch.
        docs_stmt = select(func.count(Document.id)).where(
            Document.org_id == org_id,
            Document.status == "ready",
            Document.deleted_at.is_(None),
        )
        ticket_stmt = select(func.count(Ticket.id)).where(
            Ticket.org_id == org_id,
            Ticket.status.in_(("open", "in_progress", "pending_approval")),
        )
        if department:
            ticket_stmt = ticket_stmt.where(Ticket.department == department)

        gaps_stmt = (
            select(QueryLog.query_text, func.count(QueryLog.id).label("count"))
            .where(
                QueryLog.org_id == org_id,
                QueryLog.escalated.is_(True),
            )
            .group_by(QueryLog.query_text)
            .order_by(func.count(QueryLog.id).desc())
            .limit(8)
        )

        docs_result, tickets_result, gaps_result = await asyncio.gather(
            db.execute(docs_stmt),
            db.execute(ticket_stmt),
            db.execute(gaps_stmt),
        )
        documents_ready = docs_result.scalar() or 0
        open_tickets = tickets_result.scalar() or 0
        gap_rows = gaps_result.all()
        knowledge_gaps: list[TopQuestionRow] = [
            {"question": row[0], "count": int(row[1])} for row in gap_rows
        ]

        automated_queries = max(0, total_queries - escalated_queries)
        estimated_hours_saved = round(
            automated_queries * _MINUTES_SAVED_PER_AUTOMATED_QUERY / 60, 1
        )

        escalation_rate_pct = (
            round(100.0 * escalated_queries / total_queries, 1)
            if total_queries
            else 0.0
        )
        automation_rate_pct = (
            round(100.0 * automated_queries / total_queries, 1)
            if total_queries
            else 0.0
        )

        return {
            "total_queries": total_queries,
            "queries_today": queries_today,
            "automated_queries": automated_queries,
            "escalated_queries": escalated_queries,
            "estimated_hours_saved": estimated_hours_saved,
            "automation_rate_pct": automation_rate_pct,
            "escalation_rate_pct": escalation_rate_pct,
            "documents_ready": documents_ready,
            "open_tickets": open_tickets,
            "low_confidence_unanswered": low_confidence_unanswered,
            "knowledge_gaps": knowledge_gaps,
            "department_scope": department,
        }