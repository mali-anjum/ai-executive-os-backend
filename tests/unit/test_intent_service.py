import pytest

from app.services.intent_service import INTENT_CATEGORIES, IntentService

SAMPLES = [
    ("The checkout page crashes when I click pay", "bug_report"),
    ("Can we add dark mode to the dashboard?", "feature_request"),
    ("Invoice #992 was charged twice this month", "billing"),
    ("How do I request parental leave?", "hr"),
    ("What are the office hours?", "general"),
    ("Production API returns 500 errors since deploy", "bug_report"),
    ("Please add SSO login for enterprise", "feature_request"),
    ("Refund my subscription from January", "billing"),
    ("Need help updating my W-4 form", "hr"),
    ("Who do I contact for general questions?", "general"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("message,expected_intent", SAMPLES)
async def test_intent_classification_valid_category(message, expected_intent):
    service = IntentService()
    result = await service.classify(message)
    assert result.intent in INTENT_CATEGORIES
    assert 1 <= result.priority <= 5
    assert result.summary
    assert result.department
    if expected_intent in ("billing", "bug_report", "hr", "feature_request", "general"):
        assert isinstance(result.intent, str)
