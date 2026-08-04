"""Format retrieved chunks for the knowledge agent LLM context."""

from collections.abc import Sequence

from app.models.internal.domain import RagChunkItem


def format_rag_context(chunk_items: Sequence[RagChunkItem]) -> str:
    blocks: list[str] = []
    for index, item in enumerate(chunk_items, start=1):
        page = item.get("page_number")
        page_label = str(page) if page is not None else "unknown"
        doc_id = item.get("document_id", "unknown")
        chunk_id = item.get("chunk_id", "unknown")
        header = (
            f"[Chunk {index}]\n"
            f"document_name: {item.get('document_name', 'unknown')}\n"
            f"document_id: {doc_id}\n"
            f"page_number: {page_label}\n"
            f"chunk_id: {chunk_id}\n"
            f"---\n"
        )
        blocks.append(header + item.get("content", ""))
    return "\n\n".join(blocks)
