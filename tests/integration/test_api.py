import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.http.schemas import Citation, QueryResponse

HEADERS = {
    "X-Org-Id": str(uuid.uuid4()),
    "X-User-Id": str(uuid.uuid4()),
    "X-User-Role": "admin",
}


@pytest.mark.asyncio
@patch("app.api.v1.routers.ingest.DocumentService")
@patch("app.api.v1.routers.ingest.process_document_task")
async def test_ingest_returns_202_and_queues_job(mock_task, mock_service_cls, client):
    mock_task.delay = MagicMock()
    mock_doc = MagicMock()
    mock_doc.id = uuid.uuid4()
    mock_doc.status = "pending"
    mock_service_cls.return_value.save_upload = AsyncMock(return_value=mock_doc)
    files = {"file": ("policy.md", b"# Vacation Policy\n\nEmployees get 20 days PTO.", "text/markdown")}
    response = await client.post("/api/v1/ingest", files=files, headers=HEADERS)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert "document_id" in data
    mock_task.delay.assert_called_once()


@pytest.mark.asyncio
@patch("app.agents.knowledge_agent.KnowledgeAgent.run")
async def test_query_returns_answer_with_citation(mock_run, client):
    mock_run.return_value = QueryResponse(
        answer="Employees receive 20 days of PTO.",
        citations=[
            Citation(
                chunk_id=uuid.uuid4(),
                document_name="policy.md",
                page_number=1,
                chunk_text="Employees get 20 days PTO.",
                excerpt="Employees get 20 days PTO.",
            )
        ],
        latency_ms=120,
    )
    response = await client.post(
        "/api/v1/query",
        json={"query": "How much PTO do employees get?"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"]
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["chunk_text"]


@pytest.mark.asyncio
@patch("app.agents.knowledge_agent.KnowledgeAgent.run")
async def test_query_graceful_unknown(mock_run, client):
    mock_run.return_value = QueryResponse(
        answer="I don't have enough information in the knowledge base to answer that question.",
        citations=[],
        latency_ms=50,
    )
    response = await client.post(
        "/api/v1/query",
        json={"query": "What is the Mars office policy?"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert "don't" in response.json()["answer"].lower()
