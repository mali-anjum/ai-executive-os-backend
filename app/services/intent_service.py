"""
Slack ticket classification — intent, priority, department, summary.

LLM when circuit closed; keyword heuristics when open or on 429. Used only by
ProjectAgent, not by KnowledgeAgent chat.
"""

import json
import logging
import re

from app.core.llm_classify_circuit import LlmClassifyCircuit
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

INTENT_CATEGORIES = (
    "bug_report",
    "feature_request",
    "billing",
    "hr",
    "general",
)

DEPARTMENTS = ("engineering", "billing", "hr", "product", "support")


class IntentClassification:
    def __init__(
        self,
        intent: str,
        priority: int,
        summary: str,
        department: str,
    ) -> None:
        self.intent = intent
        self.priority = priority
        self.summary = summary
        self.department = department


class IntentService:
    """One classify() per ticket line; consults LlmClassifyCircuit before calling LLM."""

    def __init__(self) -> None:
        self.llm = LLMService()

    async def classify(self, message_text: str) -> IntentClassification:
        if self.llm.has_client and not LlmClassifyCircuit.is_open():
            raw = await self.llm.classify_ticket_json(message_text)
            parsed = self._parse_json(raw) if raw else None
            if parsed:
                result = self._from_dict(parsed)
                logger.debug("intent_classified source=llm intent=%s", result.intent)
                return result

        result = self._heuristic_classify(message_text)
        logger.debug(
            "intent_classified source=heuristic intent=%s circuit_open=%s",
            result.intent,
            LlmClassifyCircuit.is_open(),
        )
        return result

    def _parse_json(self, raw: str) -> dict | None:
        try:
            match = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass
        return None

    def _from_dict(self, data: dict) -> IntentClassification:
        intent = str(data.get("intent", "general")).lower().replace(" ", "_")
        if intent not in INTENT_CATEGORIES:
            intent = "general"
        priority = int(data.get("priority", 3))
        priority = max(1, min(5, priority))
        summary = str(data.get("summary", ""))[:500] or "Incoming Slack request"
        department = str(data.get("department", "support")).lower()
        if department not in DEPARTMENTS:
            department = "support"
        return IntentClassification(intent, priority, summary, department)

    def _heuristic_classify(self, text: str) -> IntentClassification:
        lower = text.lower()
        if any(w in lower for w in ("bill", "invoice", "payment", "charge", "refund", "billing")):
            return IntentClassification("billing", 4, text[:200], "billing")
        if any(w in lower for w in ("bug", "broken", "error", "crash")):
            return IntentClassification("bug_report", 4, text[:200], "engineering")
        if any(w in lower for w in ("feature", "request", "add", "enhancement")):
            return IntentClassification("feature_request", 3, text[:200], "product")
        if any(w in lower for w in ("pto", "hr", "leave", "hiring", "onboard")):
            return IntentClassification("hr", 3, text[:200], "hr")
        return IntentClassification("general", 2, text[:200], "support")
