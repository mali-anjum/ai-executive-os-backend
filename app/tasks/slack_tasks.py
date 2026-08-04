"""
Celery bridge: Slack webhook payload → Q&A or ProjectAgent in a worker process.

FastAPI only enqueues; all LLM classify + DB writes happen here so Slack gets
200 immediately. Uses CeleryAsyncSessionLocal (NullPool) per task.
"""

import asyncio
import uuid
from typing import cast

from celery.app.task import Task

from app.core.config import settings
from app.core.database import CeleryAsyncSessionLocal
from app.core.feature_flags import flags
from app.core.slack_events import slack_message_mode
from app.agents.project_agent import ProjectAgent
from app.models.http.slack import SlackEventCallbackPayload, SlackMessageEvent
from app.services.slack_qa_service import SlackQaService
from app.tasks.celery_app import celery_app


def _run_async(coro):
    return asyncio.run(coro)


@celery_app.task(name="process_slack_event")
def process_slack_event_task(
    payload: SlackEventCallbackPayload, org_id: str | None = None
) -> str:
    async def _process():
        async with CeleryAsyncSessionLocal() as db:
            resolved_org = uuid.UUID(org_id) if org_id else None
            if not resolved_org and settings.default_org_id:
                resolved_org = uuid.UUID(settings.default_org_id)
            if not resolved_org:
                return "skipped:no_org"

            event: SlackMessageEvent = payload.get("event") or payload  # type: ignore[assignment]

            mode = slack_message_mode(event)

            if mode == "qa" and flags.SLACK_QA_ENABLED:
                qa = SlackQaService()
                ok = await qa.answer_in_channel(db, resolved_org, payload)
                return "slack_qa:ok" if ok else "slack_qa:failed"

            if not flags.PROJECT_AGENT_ENABLED:
                return "skipped:project_agent_disabled"

            agent = ProjectAgent()
            ticket_id = await agent.run(db, resolved_org, payload)
            if ticket_id:
                return f"slack_ticket:{ticket_id}"
            return "skipped"

    return _run_async(_process())


process_slack_event: Task = cast(Task, process_slack_event_task)


def enqueue_slack_event(
    payload: SlackEventCallbackPayload, org_id: str | None = None
) -> None:
    """Queue Slack event processing on the Celery worker."""
    process_slack_event.delay(payload, org_id)


def run_process_slack_event_sync(
    payload: SlackEventCallbackPayload, org_id: str | None = None
) -> str:
    """Run Slack processing in-process (integration tests)."""
    return process_slack_event.run(payload, org_id)
