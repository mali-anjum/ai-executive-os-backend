from app.core.config import settings
from app.models.internal.domain import GradedRagChunkItem, RagChunkItem


class RerankService:
    """Re-order chunks using Cohere Rerank API with score-based fallback."""

    async def rerank(
        self,
        query: str,
        chunks: list[GradedRagChunkItem],
        top_n: int | None = None,
    ) -> list[GradedRagChunkItem]:
        if not chunks:
            return []
        top_n = top_n or settings.rerank_top_k

        if settings.cohere_api_key:
            try:
                import cohere

                client = cohere.AsyncClient(api_key=settings.cohere_api_key)
                documents = [c["content"] for c in chunks]
                response = await client.rerank(
                    model="rerank-english-v3.0",
                    query=query,
                    documents=documents,
                    top_n=min(top_n, len(chunks)),
                )
                order = [r.index for r in response.results]
                return [chunks[i] for i in order]
            except Exception:
                pass

        return sorted(
            chunks,
            key=lambda c: (c.get("grade", 0), c.get("score", 0)),
            reverse=True,
        )[:top_n]
