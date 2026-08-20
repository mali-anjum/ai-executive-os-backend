"""pgvector search — permission-aware similarity over document chunk embeddings."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.tables import DocumentChunk
from app.models.internal.domain import RagChunkItem

# Permission-aware retrieval lives in the database (see migration
# 20260819000012_document_rbac_vector_retrieval.sql). The SECURITY DEFINER RPC
# enforces org isolation + document-level RBAC before any chunk leaves Postgres.
_SEARCH_DOCUMENT_CHUNKS_SQL = text(
    """
    SELECT chunk_id, document_id, document_name, content, page_number, score
    FROM public.search_document_chunks(
        CAST(:embedding AS vector),
        :org_id,
        :role,
        :department,
        :top_k,
        :min_score
    )
    """
)


def _embedding_literal(embedding: list[float]) -> str:
    """Render a float list as a pgvector literal (e.g. '[0.1,0.2,0.3]')."""
    return "[" + ",".join(f"{value:.15g}" for value in embedding) + "]"


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
        *,
        org_id: uuid.UUID | None,
        role: str,
        department: str | None,
        top_k: int = 5,
        min_score: float = 0.2,
    ) -> list[RagChunkItem]:
        """Return authorized, top-k chunks via the permission-aware RPC.

        org_id / role / department come from the already-authenticated request
        context (app/core/security.py), never from the client. Authorization is
        enforced inside PostgreSQL; rows returned here are already filtered.
        """
        result = await db.execute(
            _SEARCH_DOCUMENT_CHUNKS_SQL,
            {
                "embedding": _embedding_literal(embedding),
                "org_id": org_id,
                "role": role,
                "department": department,
                "top_k": top_k,
                "min_score": min_score,
            },
        )
        rows = result.mappings().all()
        return [
            {
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "document_name": row["document_name"],
                "content": row["content"],
                "page_number": row["page_number"],
                "score": float(row["score"]),
            }
            for row in rows
        ]
