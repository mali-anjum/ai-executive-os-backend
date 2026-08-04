"""Lightweight RAG trace spans — logs duration/attrs for knowledge agent debugging."""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger("sop_automator.trace")


class TraceSpan:
    """One timed step in the RAG pipeline (embed, retrieve, grade, generate)."""

    def __init__(self, name: str, *, parent_id: str | None = None) -> None:
        self.span_id = uuid.uuid4().hex[:16]
        self.trace_id = parent_id or self.span_id
        self.name = name
        self.start = time.perf_counter()
        self.attributes: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def finish(self) -> dict[str, Any]:
        duration_ms = int((time.perf_counter() - self.start) * 1000)
        record = {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "span_name": self.name,
            "duration_ms": duration_ms,
            **self.attributes,
        }
        logger.info("rag_span", extra={"trace": record})
        return record


@asynccontextmanager
async def trace_span(name: str, *, trace_id: str | None = None):
    span = TraceSpan(name, parent_id=trace_id)
    try:
        yield span
    finally:
        span.finish()
