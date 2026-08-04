"""Slack in-channel Q&A — route questions to KnowledgeAgent and reply in thread."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.knowledge_agent import KnowledgeAgent
from app.core.config import settings
from app.core.slack_events import extract_message_text
from app.models.http.slack import SlackEventCallbackPayload, SlackMessageEvent
from app.services.confidence_service import ConfidenceService

logger = logging.getLogger(__name__)


class SlackQaService:
    def __init__(self) -> None:
        self.agent = KnowledgeAgent()
        self.confidence = ConfidenceService()

    async def answer_in_channel(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        payload: SlackEventCallbackPayload,
    ) -> bool:
        if not settings.slack_bot_token:
            return False

        event: SlackMessageEvent = payload.get("event") or payload  # type: ignore[assignment]
        question = extract_message_text(event).strip()
        if not question:
            return False

        channel = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")
        if not channel:
            return False

        result = await self.agent.run(
            db,
            question,
            org_id=org_id,
            user_role="employee",
            user_department=None,
        )

        confidence_note = ""
        if result.confidence_score is not None:
            confidence_note = f"\n_Confidence: {result.confidence_score:.0%}_"
        if result.escalated:
            confidence_note += "\n_Escalated to support for human follow-up._"

        citation_lines = []
        for idx, cite in enumerate(result.citations[:3], start=1):
            citation_lines.append(f"{idx}. {cite.document_name}")

        body = result.answer
        if citation_lines:
            body += "\n\n*Sources:*\n" + "\n".join(citation_lines)
        body += confidence_note
        body += "\n\n_Mode: Knowledge Q&A — prefix with `!ticket` to route as a task instead._"

        try:
            from slack_sdk.web.async_client import AsyncWebClient

            client = AsyncWebClient(token=settings.slack_bot_token)
            await client.chat_postMessage(
                channel=channel,
                text=body,
                thread_ts=thread_ts,
            )
            logger.info("slack_qa_replied channel=%s thread=%s", channel, thread_ts)
            return True
        except Exception:
            logger.exception("slack_qa_reply_failed channel=%s", channel)
            return False
