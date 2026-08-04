"""One-click demo tenant — pre-loaded SOPs and sample activity for client demos."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db.tables import Document, QueryLog, Ticket
from app.tasks.document_tasks import process_document

_DEMO_SOPS: list[tuple[str, str]] = [
    (
        "employee-handbook.md",
        """# Employee Handbook

## Working hours
Standard hours are 9:00 AM – 5:00 PM local time, Monday through Friday.

## Remote work
Employees may work remotely up to 3 days per week with manager approval.

## Code of conduct
Treat colleagues with respect. Report harassment to HR immediately.
""",
    ),
    (
        "pto-policy.md",
        """# Paid Time Off (PTO) Policy

## Accrual
Full-time employees accrue 15 days PTO per year, plus 10 sick days.

## Request process
Submit PTO requests in the HR portal at least 5 business days in advance.

## Blackout dates
No PTO is approved during the last week of each fiscal quarter without VP approval.
""",
    ),
    (
        "expense-reimbursement.md",
        """# Expense Reimbursement

## Eligible expenses
Travel, meals with clients (up to $75/person), and approved software subscriptions.

## Submission deadline
Submit receipts within 30 days via the Finance portal.

## Approval
Manager approval is required for any single expense over $500.
""",
    ),
    (
        "it-support-sla.md",
        """# IT Support SLA

## Response times
- P1 (system down): 1 hour
- P2 (major impact): 4 hours
- P3 (minor issue): 1 business day

## Contact
Email support@company.internal or post in #it-helpdesk on Slack.

## Password resets
Use the self-service portal; call IT if locked out of MFA.
""",
    ),
]

_SAMPLE_QUERIES: list[tuple[str, str, float, bool]] = [
    (
        "How many PTO days do I get per year?",
        "Full-time employees accrue 15 days PTO per year, plus 10 sick days.",
        0.88,
        False,
    ),
    (
        "What is the expense limit before manager approval?",
        "Manager approval is required for any single expense over $500.",
        0.91,
        False,
    ),
    (
        "Can I work remotely every day?",
        "Employees may work remotely up to 3 days per week with manager approval.",
        0.79,
        False,
    ),
    (
        "What is the maternity leave policy in Sweden?",
        "I don't have enough information in the knowledge base to answer that question.",
        0.12,
        True,
    ),
]


class DemoSeedService:
    async def seed_org(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        upload_root = Path(settings.upload_dir)
        upload_root.mkdir(parents=True, exist_ok=True)

        doc_ids: list[str] = []
        for filename, content in _DEMO_SOPS:
            doc_id = uuid.uuid4()
            path = upload_root / f"{doc_id}.md"
            path.write_text(content, encoding="utf-8")
            document = Document(
                id=doc_id,
                org_id=org_id,
                user_id=user_id,
                filename=filename,
                storage_path=str(path),
                mime_type="text/markdown",
                file_size_bytes=len(content.encode()),
                status="pending",
                source_connector="demo_seed",
            )
            db.add(document)
            doc_ids.append(str(doc_id))

        now = datetime.now(timezone.utc)
        for query_text, answer_text, confidence, escalated in _SAMPLE_QUERIES:
            db.add(
                QueryLog(
                    org_id=org_id,
                    user_id=user_id,
                    query_text=query_text,
                    answer_text=answer_text,
                    cited_chunks=[],
                    cited_chunk_ids=[],
                    latency_ms=1200,
                    confidence_score=confidence,
                    escalated=escalated,
                    created_at=now - timedelta(hours=2),
                )
            )

        db.add(
            Ticket(
                org_id=org_id,
                source="manual",
                raw_payload={"demo": True},
                intent="support_request",
                priority=2,
                summary="[Demo] VPN access not working after password reset",
                department="it",
                status="open",
                requires_approval=False,
                approval_status="auto_approved",
            )
        )
        db.add(
            Ticket(
                org_id=org_id,
                source="manual",
                raw_payload={"demo": True},
                intent="escalation",
                priority=3,
                summary="[Demo] Low confidence: maternity leave policy in Sweden",
                department="support",
                status="open",
                requires_approval=False,
                approval_status="auto_approved",
            )
        )

        await db.commit()

        for doc_id in doc_ids:
            process_document.delay(doc_id)

        return {
            "documents_queued": len(doc_ids),
            "sample_queries": len(_SAMPLE_QUERIES),
            "sample_tickets": 2,
            "message": "Demo data seeded. Documents are indexing in the background.",
        }
