import json
import re
from collections.abc import Sequence
from typing import cast

from app.models.internal.domain import CitationRaw, RagChunkItem

_METADATA_BLOCK = re.compile(
    r"```json-metadata\s*([\s\S]*?)\s*```\s*$",
    re.IGNORECASE,
)

_CHUNK_HEADER_LEAK = re.compile(
    r"\[Chunk\s+\d+\]\s*document_name:.*?(?:\n---\n|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_FALLBACK_PREFIX = re.compile(
    r"^Based on the available documents:\s*",
    re.IGNORECASE,
)


def strip_metadata_block(raw: str) -> tuple[str, dict | None]:
    """Remove trailing json-metadata fence and return parsed JSON if valid."""
    match = _METADATA_BLOCK.search(raw.strip())
    if not match:
        return raw.strip(), None
    clean = raw[: match.start()].rstrip()
    try:
        payload = json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return clean, None
    return clean, payload if isinstance(payload, dict) else None


def merge_citations(
    metadata: dict[str, object] | None,
    chunk_items: Sequence[RagChunkItem],
    *,
    fallback_from_chunks: bool = True,
) -> list[CitationRaw]:
    """Build API citation rows from LLM json-metadata and/or retrieval chunks."""
    by_chunk: dict[str, dict] = {
        str(item["chunk_id"]): {
            "chunk_id": str(item["chunk_id"]),
            "document_id": str(item["document_id"]) if item.get("document_id") else None,
            "document_name": item["document_name"],
            "page_number": item.get("page_number"),
            "chunk_text": item["content"],
            "excerpt": item["content"][:200],
            "exact_quote_highlight": None,
            "citation_index": None,
        }
        for item in chunk_items
        if item.get("chunk_id")
    }

    raw_citations = (metadata or {}).get("citations")
    meta_list = raw_citations if isinstance(raw_citations, list) else []
    merged: list[CitationRaw] = []
    seen: set[str] = set()

    for entry in meta_list:
        if not isinstance(entry, dict):
            continue
        chunk_id = entry.get("chunk_id")
        key = str(chunk_id) if chunk_id else ""
        base = by_chunk.get(key, {})
        doc_name = entry.get("document_name") or base.get("document_name") or "unknown"
        row = {
            "chunk_id": key or base.get("chunk_id"),
            "document_id": base.get("document_id"),
            "document_name": doc_name,
            "page_number": entry.get("page_number", base.get("page_number")),
            "chunk_text": base.get("chunk_text") or entry.get("exact_quote_highlight") or "",
            "excerpt": (entry.get("exact_quote_highlight") or base.get("excerpt") or "")[:200],
            "exact_quote_highlight": entry.get("exact_quote_highlight"),
            "citation_index": entry.get("id"),
        }
        dedupe = key or f"{doc_name}:{row.get('page_number')}:{row.get('citation_index')}"
        if dedupe in seen:
            continue
        seen.add(dedupe)
        merged.append(cast(CitationRaw, row))

    if merged or not fallback_from_chunks:
        return merged

    for item in chunk_items:
        cid = str(item.get("chunk_id", ""))
        if cid and cid not in seen:
            seen.add(cid)
            merged.append(cast(CitationRaw, by_chunk[cid]))
    return merged


def _strip_trailing_ellipsis(text: str) -> str:
    return re.sub(r"(?:\.{2,}|…)\s*$", "", text.strip()).strip()


def _complete_sentences(text: str, *, max_sentences: int = 4) -> str:
    """Return full sentences only — never truncate mid-sentence with ellipsis."""
    cleaned = _strip_trailing_ellipsis(" ".join(text.split()))
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    parts = [_strip_trailing_ellipsis(p) for p in parts if p.strip()]
    parts = [p for p in parts if p]
    if not parts:
        return cleaned
    return " ".join(parts[:max_sentences])


def _extract_bullet_label(content: str, fallback: str) -> str:
    """Pull a short label from chunk content (e.g. 'Blueprint 2')."""
    first_line = content.strip().split("\n", 1)[0].strip()
    first_line = _strip_trailing_ellipsis(first_line)
    if ":" in first_line[:100]:
        label = first_line.split(":", 1)[0].strip()
        if 2 <= len(label) <= 80:
            return label
    return fallback


def sanitize_answer_text(raw: str) -> str:
    """Remove leaked RAG headers and legacy fallback prefixes from visible text."""
    text = _FALLBACK_PREFIX.sub("", raw.strip())
    text = _CHUNK_HEADER_LEAK.sub("", text)
    text = re.sub(
        r"document_name:\s*[^\n]+\n(?:(?:document_id|page_number|chunk_id):\s*[^\n]+\n)*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\.{3,}(?=\s|\[|$)", ".", text)
    text = text.replace("…", "")
    return text.strip()


def build_structured_fallback_answer(
    chunk_items: Sequence[RagChunkItem],
    *,
    query: str = "",
) -> str:
    """Readable cited summary when the LLM provider is unavailable."""
    if not chunk_items:
        return (
            "I don't have enough information in the knowledge base to answer "
            "that question."
        )

    bullets: list[str] = []
    meta_entries: list[dict[str, object]] = []

    for index, item in enumerate(chunk_items[:4], start=1):
        doc_name = item.get("document_name") or "unknown"
        page = item.get("page_number")
        page_label = str(page) if page is not None else "?"
        raw_content = item.get("content", "")
        label = _extract_bullet_label(
            raw_content, doc_name.rsplit(".", 1)[0].replace("_", " ")
        )
        body_source = raw_content
        lines = raw_content.strip().split("\n", 1)
        first_line = lines[0]
        if ":" in first_line[:100]:
            body_source = first_line.split(":", 1)[1].strip()
            if len(lines) > 1:
                body_source = f"{body_source} {lines[1].strip()}"
        body = _strip_trailing_ellipsis(
            _complete_sentences(body_source, max_sentences=4)
        )
        if not body:
            continue
        bullets.append(
            f"- **{label}:** {body} [Source: {doc_name}, Page: {page_label}]"
        )
        chunk_id = item.get("chunk_id")
        highlight = _complete_sentences(raw_content, max_sentences=2) or body
        meta_entries.append(
            {
                "id": index,
                "document_name": doc_name,
                "page_number": page,
                "chunk_id": str(chunk_id) if chunk_id else None,
                "exact_quote_highlight": highlight,
            }
        )

    if not bullets:
        return (
            "I don't have enough information in the knowledge base to answer "
            "that question."
        )

    metadata = json.dumps({"citations": meta_entries}, indent=2)
    return (
        f"{chr(10).join(bullets)}\n\n"
        f"```json-metadata\n{metadata}\n```"
    )


def parse_knowledge_answer(
    raw: str, chunk_items: Sequence[RagChunkItem]
) -> tuple[str, list[CitationRaw]]:
    clean, metadata = strip_metadata_block(raw)
    clean = sanitize_answer_text(clean)
    citations = merge_citations(metadata, chunk_items)
    return clean, citations
