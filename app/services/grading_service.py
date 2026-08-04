import re
from collections.abc import Sequence

from app.models.internal.domain import GradedRagChunkItem, RagChunkItem
from app.services.llm_service import LLMService


class GradingService:
    """LLM grades chunk relevance 1-5; chunks scoring <=2 are dropped."""

    def __init__(self) -> None:
        self.llm = LLMService()

    async def grade_chunk(self, query: str, chunk_text: str) -> int:
        if not chunk_text.strip():
            return 1

        if self.llm.has_openai_client:
            prompt = (
                f"Rate how relevant this document chunk is to the user question.\n"
                f"Question: {query}\n\nChunk:\n{chunk_text[:1500]}\n\n"
                "Reply with ONLY a single integer from 1 (irrelevant) to 5 (highly relevant)."
            )
            raw = await self.llm.generate_answer(
                "Return only a number 1-5.",
                prompt,
            )
            match = re.search(r"[1-5]", raw)
            if match:
                return int(match.group())

        return self._heuristic_grade(query, chunk_text)

    def _heuristic_grade(self, query: str, chunk_text: str) -> int:
        q_lower = query.lower()
        meta_signals = (
            "document",
            "upload",
            "uploaded",
            "file",
            "pdf",
            "sop",
            "policy",
            "knowledge",
            "summary",
            "information",
        )
        if chunk_text.strip() and any(signal in q_lower for signal in meta_signals):
            return 3

        q_words = {w.lower() for w in re.findall(r"\w+", query) if len(w) > 3}
        c_words = {w.lower() for w in re.findall(r"\w+", chunk_text)}
        if not q_words:
            return 3
        overlap = len(q_words & c_words) / len(q_words)
        if overlap >= 0.5:
            return 5
        if overlap >= 0.25:
            return 4
        if overlap >= 0.1:
            return 3
        if overlap > 0:
            return 2
        return 1

    async def filter_chunks(
        self,
        query: str,
        chunks: Sequence[RagChunkItem],
        min_grade: int = 3,
    ) -> list[GradedRagChunkItem]:
        graded: list[GradedRagChunkItem] = []
        for item in chunks:
            score = await self.grade_chunk(query, item["content"])
            row: GradedRagChunkItem = {**item, "grade": score}
            if score >= min_grade:
                graded.append(row)
        return graded
