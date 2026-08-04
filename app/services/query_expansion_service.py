"""Query expansion — rewrite short/ambiguous queries before retrieval."""

from __future__ import annotations

import re


class QueryExpansionService:
    """Lightweight expansion without extra LLM calls (fast, deterministic)."""

    def expand(self, query: str) -> list[str]:
        base = re.sub(r"\s+", " ", query.strip())
        if not base:
            return []

        variants: list[str] = [base]
        lower = base.lower()

        if not lower.endswith("?"):
            variants.append(f"{base}?")

        if len(base.split()) <= 6:
            variants.append(f"company policy and procedure: {base}")
            variants.append(f"information about {base}")

        # Dedupe while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for v in variants:
            key = v.lower()
            if key not in seen:
                seen.add(key)
                unique.append(v)
        return unique[:3]
