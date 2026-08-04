from app.services.query_expansion_service import QueryExpansionService


def test_expand_adds_variants_for_short_query():
    service = QueryExpansionService()
    variants = service.expand("PTO policy")
    assert variants[0] == "PTO policy"
    assert len(variants) >= 2
    assert any("company policy" in v.lower() for v in variants)


def test_expand_dedupes_identical_variants():
    service = QueryExpansionService()
    variants = service.expand("  remote work  ")
    assert variants == list(dict.fromkeys(variants))
