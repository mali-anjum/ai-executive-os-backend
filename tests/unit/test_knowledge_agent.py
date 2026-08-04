import pytest

from app.agents.knowledge_agent import KnowledgeAgent
from app.core.config import settings


@pytest.mark.asyncio
async def test_grade_relevance_keeps_top_chunks_when_filter_empty(monkeypatch):
    agent = KnowledgeAgent()
    chunks = [
        {"chunk_id": "a", "content": "First chunk", "document_name": "a.pdf", "score": 0.05},
        {"chunk_id": "b", "content": "Second chunk", "document_name": "a.pdf", "score": 0.12},
    ]

    async def _drop_all(_query, _chunks, min_grade=3):
        return []

    monkeypatch.setattr(agent.grader, "filter_chunks", _drop_all)
    state = await agent._grade_relevance({"parsed_query": "anything", "chunk_items": chunks})
    kept = state["chunk_items"]
    assert len(kept) == min(len(chunks), settings.rerank_top_k)
    assert kept[0]["score"] == 0.12


@pytest.mark.asyncio
async def test_retrieve_passes_zero_min_score_for_hash_embeddings(monkeypatch):
    agent = KnowledgeAgent()
    monkeypatch.setattr(
        type(agent.embedder),
        "uses_openai_embeddings",
        property(lambda _self: False),
    )

    captured: dict = {}

    async def _fake_embed(_text: str) -> list[float]:
        return [0.0] * settings.embedding_dimensions

    async def _fake_search(
        _db, embedding, org_id=None, top_k=5, min_score=0.2, access_filter=None
    ):
        captured["min_score"] = min_score
        captured["access_filter"] = access_filter
        return []

    monkeypatch.setattr(agent.embedder, "embed", _fake_embed)
    monkeypatch.setattr(agent.vector, "similarity_search", _fake_search)

    await agent._retrieve(None, "test query", None)
    assert captured["min_score"] == 0.0
