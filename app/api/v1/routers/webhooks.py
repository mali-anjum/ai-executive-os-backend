"""
Inbound integrations — currently Slack Events API only.

Verify signature → dedupe (Redis) → enqueue Celery. Never creates tickets inline;
that keeps Slack retries cheap and response time under Slack's 3s expectation.
"""

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.core.feature_flags import flags
from app.core.slack_dedupe import slack_event_dedupe
from app.core.slack_events import should_process_slack_message, slack_dedupe_key
from app.core.slack_verify import verify_slack_signature
from app.models.http.errors import SlackChallengeResponse, SlackWebhookAck
from app.models.http.slack import SlackEventCallbackPayload
from app.tasks.slack_tasks import enqueue_slack_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook/slack")
async def slack_webhook(request: Request):
    if not flags.SLACK_WEBHOOK_ENABLED:
        raise HTTPException(status_code=404, detail="Slack webhook is not enabled")
    if not flags.PROJECT_AGENT_ENABLED and not flags.SLACK_QA_ENABLED:
        raise HTTPException(
            status_code=404,
            detail="Slack webhook requires PROJECT_AGENT_ENABLED or SLACK_QA_ENABLED",
        )

    body = await request.body()
    verify_slack_signature(
        body,
        request.headers.get("X-Slack-Request-Timestamp"),
        request.headers.get("X-Slack-Signature"),
    )

    payload: SlackEventCallbackPayload = json.loads(body.decode("utf-8"))

    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge") or ""
        return SlackChallengeResponse(challenge=challenge)

    if payload.get("type") == "event_callback":
        event = payload.get("event") or {}
        if should_process_slack_message(event):
            dedupe_key = slack_dedupe_key(payload, event)
            claimed = await slack_event_dedupe.claim(dedupe_key)
            if claimed:
                resolved_org: uuid.UUID | None = None
                if settings.default_org_id:
                    resolved_org = uuid.UUID(settings.default_org_id)
                logger.info(
                    "slack_webhook_enqueue event_id=%s channel=%s ts=%s dedupe_key=%s",
                    payload.get("event_id"),
                    event.get("channel"),
                    event.get("ts"),
                    dedupe_key,
                )
                enqueue_slack_event(
                    payload,
                    str(resolved_org) if resolved_org else None,
                )
            else:
                logger.info(
                    "slack_webhook_dedupe_skip event_id=%s dedupe_key=%s",
                    payload.get("event_id"),
                    dedupe_key,
                )

    return SlackWebhookAck()
