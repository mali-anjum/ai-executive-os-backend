import pytest

from app.services.grading_service import GradingService


@pytest.mark.asyncio
async def test_grade_returns_score_between_1_and_5():
    service = GradingService()
    score = await service.grade_chunk(
        "What is the vacation policy?",
        "Employees receive twenty days of paid time off per year.",
    )
    assert 1 <= score <= 5


@pytest.mark.asyncio
async def test_filter_drops_low_relevance_chunks():
    service = GradingService()
    chunks = [
        {"content": "Mars colonization rocket fuel requirements"},
        {"content": "Employees receive 20 days PTO annually per handbook."},
    ]
    filtered = await service.filter_chunks(
        "How much vacation do employees get?", chunks, min_grade=3
    )
    assert len(filtered) <= len(chunks)
    for item in filtered:
        assert item["grade"] > 2


def test_heuristic_meta_document_query_keeps_chunks():
    service = GradingService()
    score = service._heuristic_grade(
        "give me any information about the uploaded document please",
        "AI Executive OS project blueprint and rollout milestones.",
    )
    assert score >= 3


@pytest.mark.asyncio
async def test_filter_respects_min_grade():
    service = GradingService()
    chunks = [{"content": "Annual PTO policy grants twenty days per year."}]
    filtered = await service.filter_chunks(
        "tell me about the uploaded document",
        chunks,
        min_grade=3,
    )
    assert len(filtered) == 1


@pytest.mark.asyncio
async def test_irrelevant_query_grades_low():
    service = GradingService()
    score = await service.grade_chunk(
        "What is the cafeteria menu on Mars?",
        "Annual performance review deadlines are in Q4.",
    )
    assert 1 <= score <= 5
