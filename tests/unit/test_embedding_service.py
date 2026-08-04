import pytest

from app.core.config import settings
from app.services.embedding_service import EmbeddingService


@pytest.mark.asyncio
async def test_embedding_returns_1536_dimensions():
    service = EmbeddingService()
    vector = await service.embed("Any input text for embedding.")
    assert len(vector) == settings.embedding_dimensions
    assert all(isinstance(v, float) for v in vector)


@pytest.mark.asyncio
async def test_embedding_empty_text_raises():
    service = EmbeddingService()
    with pytest.raises(ValueError):
        await service.embed("")
