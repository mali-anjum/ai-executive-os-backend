"""RAG evaluation metrics — confidence, escalation, and feedback accuracy."""

from __future__ import annotations

import uuid

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.tables import QueryLog


class EvaluationService:
    async def get_metrics(self, db: AsyncSession, org_id: uuid.UUID) -> dict:
        # Single aggregate query for all counts + avg confidence in one round-trip.
        agg_stmt = select(
            func.count(QueryLog.id).label("total"),
            func.count(
                case((QueryLog.escalated.is_(True), 1))
            ).label("escalated"),
            func.count(
                case(
                    (
                        QueryLog.confidence_score.isnot(None)
                        & (QueryLog.confidence_score < 0.45),
                        1,
                    )
                )
            ).label("low_confidence"),
            func.count(
                case((QueryLog.feedback == "positive", 1))
            ).label("positive"),
            func.count(
                case((QueryLog.feedback == "negative", 1))
            ).label("negative"),
            func.avg(QueryLog.confidence_score).label("avg_confidence"),
        ).where(QueryLog.org_id == org_id)

        row = (await db.execute(agg_stmt)).one()

        total = row.total or 0
        escalated = row.escalated or 0
        low_confidence = row.low_confidence or 0
        positive = row.positive or 0
        negative = row.negative or 0

        feedback_total = positive + negative
        accuracy_pct = (
            round(100.0 * positive / feedback_total, 1) if feedback_total else None
        )
        escalation_rate_pct = (
            round(100.0 * escalated / total, 1) if total else 0.0
        )
        avg_confidence_pct = (
            round(float(row.avg_confidence) * 100, 1)
            if row.avg_confidence is not None
            else None
        )

        unanswered_stmt = (
            select(QueryLog.query_text, func.count(QueryLog.id).label("count"))
            .where(
                QueryLog.org_id == org_id,
                QueryLog.escalated.is_(True),
            )
            .group_by(QueryLog.query_text)
            .order_by(func.count(QueryLog.id).desc())
            .limit(10)
        )
        unanswered_rows = (await db.execute(unanswered_stmt)).all()

        return {
            "total_queries": total,
            "escalated_queries": escalated,
            "low_confidence_queries": low_confidence,
            "positive_feedback": positive,
            "negative_feedback": negative,
            "accuracy_pct": accuracy_pct,
            "escalation_rate_pct": escalation_rate_pct,
            "avg_confidence_pct": avg_confidence_pct,
            "unanswered_questions": [
                {"question": row[0], "count": int(row[1])} for row in unanswered_rows
            ],
        }

    async def get_unanswered_report(
        self, db: AsyncSession, org_id: uuid.UUID
    ) -> dict:
        metrics = await self.get_metrics(db, org_id)

        low_conf_stmt = (
            select(QueryLog.query_text, func.count(QueryLog.id).label("count"))
            .where(
                QueryLog.org_id == org_id,
                QueryLog.escalated.is_(False),
                QueryLog.confidence_score.isnot(None),
                QueryLog.confidence_score < 0.45,
            )
            .group_by(QueryLog.query_text)
            .order_by(func.count(QueryLog.id).desc())
            .limit(15)
        )
        low_conf_rows = (await db.execute(low_conf_stmt)).all()

        negative_stmt = (
            select(QueryLog.query_text, func.count(QueryLog.id).label("count"))
            .where(QueryLog.org_id == org_id, QueryLog.feedback == "negative")
            .group_by(QueryLog.query_text)
            .order_by(func.count(QueryLog.id).desc())
            .limit(15)
        )
        negative_rows = (await db.execute(negative_stmt)).all()

        escalated = metrics["unanswered_questions"]
        low_confidence = [
            {"question": row[0], "count": int(row[1])} for row in low_conf_rows
        ]
        negative_feedback = [
            {"question": row[0], "count": int(row[1])} for row in negative_rows
        ]
        return {
            "escalated": escalated,
            "low_confidence": low_confidence,
            "negative_feedback": negative_feedback,
            "total_gaps": len(escalated) + len(low_confidence) + len(negative_feedback),
        }

    async def set_feedback(
        self,
        db: AsyncSession,
        query_id: uuid.UUID,
        org_id: uuid.UUID,
        feedback: str,
    ) -> bool:
        result = await db.execute(
            select(QueryLog).where(QueryLog.id == query_id, QueryLog.org_id == org_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        row.feedback = feedback
        await db.commit()
        return True
