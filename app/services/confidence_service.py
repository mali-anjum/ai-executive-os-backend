"""Compute RAG answer confidence from retrieval grades and vector scores."""

from app.models.internal.domain import GradedRagChunkItem


class ConfidenceService:
    """Maps chunk grades (1–5) and cosine scores into a 0–1 confidence value."""

    LOW_CONFIDENCE_THRESHOLD = 0.45

    def compute(self, chunks: list[GradedRagChunkItem]) -> float:
        if not chunks:
            return 0.0

        grade_scores: list[float] = []
        vector_scores: list[float] = []
        for chunk in chunks:
            grade = chunk.get("grade")
            if grade is not None:
                grade_scores.append(max(0.0, min(1.0, (float(grade) - 1) / 4)))
            score = chunk.get("score")
            if score is not None:
                vector_scores.append(max(0.0, min(1.0, float(score))))

        grade_avg = sum(grade_scores) / len(grade_scores) if grade_scores else 0.0
        vector_avg = sum(vector_scores) / len(vector_scores) if vector_scores else 0.0

        if grade_scores and vector_scores:
            return round(0.6 * grade_avg + 0.4 * vector_avg, 3)
        if grade_scores:
            return round(grade_avg, 3)
        return round(vector_avg, 3)

    def is_low_confidence(self, confidence: float) -> bool:
        return confidence < self.LOW_CONFIDENCE_THRESHOLD
