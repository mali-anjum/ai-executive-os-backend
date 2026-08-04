"""RAG evaluation harness — golden questions with pass/fail regression checks."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.knowledge_agent import KnowledgeAgent

# Golden cases — extend after seeding demo SOPs for best results.
GOLDEN_CASES: list[dict] = [
    {
        "id": "pto-accrual",
        "question": "How many PTO days do full-time employees get per year?",
        "expect_contains": ["15"],
        "min_confidence": 0.35,
    },
    {
        "id": "expense-approval",
        "question": "When is manager approval required for expenses?",
        "expect_contains": ["500"],
        "min_confidence": 0.35,
    },
    {
        "id": "remote-work",
        "question": "How many remote work days are allowed per week?",
        "expect_contains": ["3"],
        "min_confidence": 0.35,
    },
    {
        "id": "it-p1-sla",
        "question": "What is the P1 IT support response time?",
        "expect_contains": ["hour"],
        "min_confidence": 0.35,
    },
    {
        "id": "out-of-scope",
        "question": "What is the corporate tax rate in Norway?",
        "expect_contains": [],
        "max_confidence": 0.5,
        "expect_escalated_or_low": True,
    },
]


class EvaluationHarnessService:
    def list_cases(self) -> list[dict]:
        return [
            {
                "id": c["id"],
                "question": c["question"],
                "expect_contains": c.get("expect_contains", []),
                "min_confidence": c.get("min_confidence"),
                "max_confidence": c.get("max_confidence"),
                "expect_escalated_or_low": c.get("expect_escalated_or_low", False),
            }
            for c in GOLDEN_CASES
        ]

    async def run_harness(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        *,
        user_role: str = "admin",
        user_department: str | None = None,
    ) -> dict:
        agent = KnowledgeAgent()
        results: list[dict] = []
        passed = 0

        for case in GOLDEN_CASES:
            response = await agent.run(
                db,
                case["question"],
                org_id=org_id,
                user_role=user_role,
                user_department=user_department,
            )
            answer_lower = (response.answer or "").lower()
            confidence = response.confidence_score or 0.0

            contains_ok = all(
                token.lower() in answer_lower
                for token in case.get("expect_contains", [])
            )
            min_conf = case.get("min_confidence")
            max_conf = case.get("max_confidence")
            conf_ok = True
            if min_conf is not None:
                conf_ok = confidence >= min_conf
            if max_conf is not None:
                conf_ok = conf_ok and confidence <= max_conf

            escalated_ok = True
            if case.get("expect_escalated_or_low"):
                escalated_ok = bool(
                    response.escalated or confidence < 0.45
                )

            ok = contains_ok and conf_ok and escalated_ok
            if ok:
                passed += 1

            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "passed": ok,
                    "answer_preview": (response.answer or "")[:240],
                    "confidence_score": confidence,
                    "escalated": response.escalated,
                    "checks": {
                        "contains": contains_ok,
                        "confidence": conf_ok,
                        "escalation_policy": escalated_ok,
                    },
                }
            )

        total = len(GOLDEN_CASES)
        accuracy_pct = round(100.0 * passed / total, 1) if total else 0.0
        return {
            "total_cases": total,
            "passed": passed,
            "failed": total - passed,
            "accuracy_pct": accuracy_pct,
            "results": results,
        }
