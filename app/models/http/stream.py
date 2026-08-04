"""SSE payload types for POST /api/v1/query/stream."""

from __future__ import annotations

from typing import Literal, TypedDict, cast

from app.models.http.schemas import Citation


class StreamTokenEvent(TypedDict):
    type: Literal["token"]
    content: str


class StreamErrorEvent(TypedDict):
    type: Literal["error"]
    message: str


# JSON shape emitted by Citation.model_dump(mode="json") on the done event.
CitationJson = dict[str, str | int | None]


class RetrievalTraceJson(TypedDict, total=False):
    original_query: str
    expanded_queries: list[str]
    candidates: list[dict]


class StreamDoneEvent(TypedDict, total=False):
    type: Literal["done"]
    answer: str
    citations: list[CitationJson]
    latency_ms: int
    confidence_score: float
    escalated: bool
    escalation_ticket_id: str | None
    query_log_id: str | None
    retrieval_trace: RetrievalTraceJson


def citation_to_json(citation: Citation) -> CitationJson:
    return cast(CitationJson, citation.model_dump(mode="json"))
