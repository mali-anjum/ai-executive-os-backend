import asyncio
import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.helpers.slack_signing import sign_slack_request

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
ORG_ID = str(uuid.uuid4())


@pytest.fixture(autouse=True)
def slack_settings(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.default_org_id", ORG_ID)


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.mark.asyncio
@patch("app.api.v1.routers.webhooks.verify_slack_signature")
async def test_url_verification_returns_challenge(mock_verify, client):
    body = _load("slack_url_verification.json")
    response = await client.post("/api/v1/webhook/slack", content=body)
    assert response.status_code == 200
    assert response.json()["challenge"] == json.loads(body)["challenge"]
    mock_verify.assert_called_once()


@pytest.mark.asyncio
@patch("app.api.v1.routers.webhooks.verify_slack_signature")
@patch("app.api.v1.routers.webhooks.slack_event_dedupe")
@patch("app.api.v1.routers.webhooks.enqueue_slack_event")
async def test_valid_event_enqueues_celery(mock_enqueue, mock_dedupe, mock_verify, client):
    mock_dedupe.claim = AsyncMock(return_value=True)
    body = _load("slack_message_event.json")
    response = await client.post("/api/v1/webhook/slack", content=body)
    assert response.status_code == 200
    assert response.json()["ok"] is True
    mock_enqueue.assert_called_once()


@pytest.mark.asyncio
@patch("app.api.v1.routers.webhooks.enqueue_slack_event")
async def test_invalid_signature_returns_401(mock_enqueue, client):
    body = _load("slack_message_event.json")
    with patch(
        "app.api.v1.routers.webhooks.verify_slack_signature",
        side_effect=__import__("fastapi").HTTPException(status_code=401, detail="bad sig"),
    ):
        response = await client.post("/api/v1/webhook/slack", content=body)
    assert response.status_code == 401
    mock_enqueue.assert_not_called()


@pytest.mark.asyncio
@patch("app.tasks.slack_tasks._run_async")
@patch("app.tasks.slack_tasks.ProjectAgent")
async def test_slack_task_invokes_project_agent(MockAgent, mock_run_async):
    ticket_id = uuid.uuid4()
    MockAgent.return_value.run = AsyncMock(return_value=ticket_id)
    mock_run_async.return_value = str(ticket_id)

    from app.tasks.slack_tasks import run_process_slack_event_sync

    payload = json.loads(_load("slack_message_event.json"))
    result = run_process_slack_event_sync(payload, ORG_ID)
    assert result == str(ticket_id)
    mock_run_async.assert_called_once()


@pytest.mark.asyncio
@patch("app.api.v1.routers.webhooks.verify_slack_signature")
@patch("app.api.v1.routers.webhooks.slack_event_dedupe")
@patch("app.api.v1.routers.webhooks.enqueue_slack_event")
async def test_duplicate_event_id_enqueues_once(mock_enqueue, mock_dedupe, mock_verify, client):
    mock_dedupe.claim = AsyncMock(side_effect=[True] + [False] * 49)
    body = _load("slack_message_event.json")

    async def post_once():
        return await client.post("/api/v1/webhook/slack", content=body)

    responses = await asyncio.gather(*[post_once() for _ in range(50)])
    assert all(r.status_code == 200 for r in responses)
    assert mock_enqueue.call_count == 1


@pytest.mark.asyncio
async def test_billing_message_classified_to_billing_department():
    from app.services.intent_service import IntentService

    service = IntentService()
    result = await service.classify(
        "Invoice #8842 was charged twice this month — billing issue"
    )
    assert result.department == "billing"
