"""VectorService — permission-aware RPC retrieval and row mapping."""

import uuid

import pytest

from app.services.vector_service import VectorService, _embedding_literal


def test_embedding_literal_renders_pgvector_string():
    assert _embedding_literal([0.1, 0.25, -1.0]) == "[0.1,0.25,-1]"
    assert _embedding_literal([1.0]) == "[1]"


class _FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return _FakeMappings(self._rows)


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows
        self.stmt = None
        self.params = None

    async def execute(self, stmt, params):
        self.stmt = stmt
        self.params = params
        return _FakeResult(self._rows)


@pytest.mark.asyncio
async def test_similarity_search_calls_rpc_with_server_derived_context():
    org_id = uuid.uuid4()
    db = _FakeDB([])
    service = VectorService()

    result = await service.similarity_search(
        db,
        [0.5, 0.6],
        org_id=org_id,
        role="employee",
        department="sales",
        top_k=8,
        min_score=0.3,
    )

    assert result == []
    assert "search_document_chunks" in str(db.stmt)
    assert db.params["org_id"] == org_id
    assert db.params["role"] == "employee"
    assert db.params["department"] == "sales"
    assert db.params["top_k"] == 8
    assert db.params["min_score"] == 0.3
    assert db.params["embedding"] == "[0.5,0.6]"


@pytest.mark.asyncio
async def test_similarity_search_maps_rpc_rows_to_rag_chunks():
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    db = _FakeDB(
        [
            {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "document_name": "policy.pdf",
                "content": "PTO policy text",
                "page_number": 3,
                "score": 0.91,
            }
        ]
    )
    service = VectorService()

    result = await service.similarity_search(
        db,
        [0.0, 0.0],
        org_id=uuid.uuid4(),
        role="manager",
        department=None,
    )

    assert result == [
        {
            "chunk_id": chunk_id,
            "document_id": doc_id,
            "document_name": "policy.pdf",
            "content": "PTO policy text",
            "page_number": 3,
            "score": 0.91,
        }
    ]
