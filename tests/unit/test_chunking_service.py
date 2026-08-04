import pytest

from app.services.chunking_service import ChunkingService


@pytest.mark.asyncio
async def test_chunk_document_produces_chunks_under_max_tokens():
    service = ChunkingService(max_tokens=800)
    text = "Sample SOP text. " * 500
    chunks = service.chunk_text(text)
    assert len(chunks) > 0
    for chunk in chunks:
        assert service.count_tokens(chunk.content) <= 800
        assert chunk.content.strip()


def test_chunk_empty_text_returns_no_chunks():
    service = ChunkingService()
    assert service.chunk_text("") == []
    assert service.chunk_text("   ") == []
