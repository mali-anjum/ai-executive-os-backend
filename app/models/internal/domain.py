"""Typed structures passed between services/agents (not HTTP-bound)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing_extensions import TypedDict, cast


class RagChunkItem(TypedDict):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    document_name: str
    page_number: int | None
    score: float


class GradedRagChunkItem(RagChunkItem, total=False):
    grade: int


def as_graded_chunks(items: Sequence[RagChunkItem]) -> list[GradedRagChunkItem]:
    """Rag chunks are valid graded chunks before a grade is assigned."""
    return cast(list[GradedRagChunkItem], list(items))


class CitationRaw(TypedDict, total=False):
    chunk_id: str | uuid.UUID
    document_id: str | uuid.UUID | None
    document_name: str
    page_number: int | None
    chunk_text: str
    excerpt: str | None
    exact_quote_highlight: str | None
    citation_index: int | None


class TopQuestionRow(TypedDict):
    question: str
    count: int


class AnalyticsMetrics(TypedDict):
    queries_today: int
    latency_p50_ms: int | None
    latency_p95_ms: int | None
    documents_indexed: int
    top_questions: list[TopQuestionRow]
