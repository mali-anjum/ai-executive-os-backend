import uuid
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.tables import Document, QueryLog
from app.models.internal.domain import AnalyticsMetrics, TopQuestionRow


class AnalyticsService:
    async def get_dashboard_metrics(
        self, db: AsyncSession, org_id: uuid.UUID
    ) -> AnalyticsMetrics:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Single aggregate query for all counts + percentiles in one round-trip.
        # Uses SQL percentile_cont instead of loading all rows into Python.
        agg_stmt = select(
            func.count(QueryLog.id).label("total_queries"),
            func.count(
                case((QueryLog.created_at >= today_start, 1), else_=0)
            ).label("queries_today"),
            func.count(Document.id).label("documents_indexed"),
            func.percentile_cont(0.50).within_group(
                QueryLog.latency_ms.asc()
            ).label("p50"),
            func.percentile_cont(0.95).within_group(
                QueryLog.latency_ms.asc()
            ).label("p95"),
        ).select_from(QueryLog).outerjoin(
            Document,
            (Document.org_id == org_id)
            & (Document.status == "ready")
            & (Document.deleted_at.is_(None)),
        ).where(QueryLog.org_id == org_id)

        row = (await db.execute(agg_stmt)).one()

        # Top questions (separate query, grouped)
        top_questions_stmt = (
            select(QueryLog.query_text, func.count(QueryLog.id).label("count"))
            .where(QueryLog.org_id == org_id)
            .group_by(QueryLog.query_text)
            .order_by(func.count(QueryLog.id).desc())
            .limit(10)
        )
        top_rows = (await db.execute(top_questions_stmt)).all()
        top_questions: list[TopQuestionRow] = [
            {"question": row[0], "count": int(row[1])} for row in top_rows
        ]

        return {
            "queries_today": row.queries_today or 0,
            "latency_p50_ms": int(row.p50) if row.p50 is not None else None,
            "latency_p95_ms": int(row.p95) if row.p95 is not None else None,
            "documents_indexed": row.documents_indexed or 0,
            "top_questions": top_questions,
        }
