import uuid
from unittest.mock import AsyncMock, patch

import pytest

HEADERS = {
    "X-Org-Id": str(uuid.uuid4()),
    "X-User-Id": str(uuid.uuid4()),
    "X-User-Role": "employee",
}


@pytest.mark.asyncio
@patch("app.agents.knowledge_agent.KnowledgeAgent.run_stream")
async def test_streaming_returns_chunked_sse(mock_stream, client):
    async def fake_stream(*args, **kwargs):
        yield '{"type": "token", "content": "Hello"}'
        yield '{"type": "done", "answer": "Hello", "citations": [], "latency_ms": 10}'

    mock_stream.return_value = fake_stream()

    response = await client.post(
        "/api/v1/query/stream",
        json={"query": "test"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = response.text
    assert "data:" in body
    assert "Hello" in body
