"""pgvector search — org-scoped similarity over document chunk embeddings."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.tables import Document, DocumentChunk


class VectorService:
    """Persist chunks and run top-k cosine search for the Knowledge Agent."""

    async def store_chunks(
        self, db: AsyncSession, chunks: list[DocumentChunk]
    ) -> None:
        db.add_all(chunks)
        await db.commit()

    async def similarity_search(
        self,
        db: AsyncSession,
        embedding: list[float],
        org_id: uuid.UUID | None = None,
        top_k: int = 5,
        min_score: float = 0.2,
        access_filter=None,
    ) -> list[tuple[DocumentChunk, float, Document]]:
        distance = DocumentChunk.embedding.cosine_distance(embedding)
        stmt = (
            select(DocumentChunk, (1 - distance).label("score"), Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.embedding.isnot(None))
            .where(Document.deleted_at.is_(None))
        )
        if org_id is not None:
            stmt = stmt.where(Document.org_id == org_id)
        if access_filter is not None and access_filter is not True:
            stmt = stmt.where(access_filter)
        stmt = stmt.order_by(distance).limit(top_k)
        result = await db.execute(stmt)
        rows = result.all()
        return [
            (row[0], float(row[1]), row[2])
            for row in rows
            if row[1] is not None and float(row[1]) >= min_score
        ]
