"""
Circuit breaker for Slack ticket LLM classification.

Architecture (ingestion path):
  Slack webhook → Celery → IntentService.classify()
                              ├─ circuit closed → LLMService.classify_ticket_json()
                              └─ circuit open   → heuristic rules (instant)

On provider 429, LLMService trips this breaker; all classify calls in the
cooldown window skip the API. Multi-line Slack posts are classified in parallel,
so per-line exponential backoff would stack delays — a single trip + heuristics
keeps ingestion fast and cost-bounded. RAG/chat paths do not use this breaker.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

# After a 429, skip LLM classify calls for this window (ticket path uses heuristics).
_CLASSIFY_COOLDOWN_SECONDS = 60.0


class LlmClassifyCircuit:
    """Process-wide open/closed gate for ticket classify LLM calls (monotonic clock)."""

    _open_until: float = 0.0

    @classmethod
    def is_open(cls) -> bool:
        return time.monotonic() < cls._open_until

    @classmethod
    def trip(cls, *, reason: str = "rate_limited", cooldown_seconds: float | None = None) -> None:
        delay = cooldown_seconds if cooldown_seconds is not None else _CLASSIFY_COOLDOWN_SECONDS
        cls._open_until = time.monotonic() + delay
        logger.warning(
            "llm_classify_circuit_open reason=%s cooldown_seconds=%.0f",
            reason,
            delay,
        )

    @classmethod
    def reset(cls) -> None:
        cls._open_until = 0.0
