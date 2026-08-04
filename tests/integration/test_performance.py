import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.http.schemas import Citation, QueryResponse

HEADERS = {
    "X-Org-Id": str(uuid.uuid4()),
    "X-User-Id": str(uuid.uuid4()),
    "X-User-Role": "employee",
}


@pytest.mark.asyncio
@patch("app.agents.knowledge_agent.KnowledgeAgent.run")
async def test_query_latency_under_3_seconds(mock_run, client):
    mock_run.return_value = QueryResponse(
        answer="ok",
        citations=[
            Citation(
                chunk_id=uuid.uuid4(),
                document_name="handbook.pdf",
                page_number=1,
                chunk_text="PTO policy text",
                excerpt="PTO policy",
            )
        ],
        latency_ms=500,
    )

    start = time.perf_counter()
    response = await client.post(
        "/api/v1/query",
        json={"query": "vacation policy"},
        headers=HEADERS,
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 3.0
