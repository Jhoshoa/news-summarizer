from src.processors.story_coverage import build_coverage_summary


def _claim(confidence: str, text: str = "dato") -> dict:
    return {"claim": text, "confidence": confidence, "claim_type": None, "article_id": 1}


def test_build_coverage_summary_groups_claims_by_confidence():
    result = build_coverage_summary(
        sources=["Unitel", "ElDeber"],
        claims=[
            _claim("multi_source", "confirmado por dos medios"),
            _claim("single_source", "solo un medio lo reporta"),
            _claim("official_statement", "segun el comunicado oficial"),
        ],
    )

    assert result["source_count"] == 2
    assert result["sources"] == ["ElDeber", "Unitel"]
    assert [c["claim"] for c in result["confirmed_by_multiple_sources"]] == ["confirmado por dos medios"]
    assert [c["claim"] for c in result["reported_by_single_source"]] == ["solo un medio lo reporta"]
    assert [c["claim"] for c in result["based_on_official_statement"]] == ["segun el comunicado oficial"]


def test_build_coverage_summary_dedupes_and_sorts_sources():
    result = build_coverage_summary(sources=["Unitel", "unitel".title(), "", None, "ElDeber"], claims=[])
    assert result["sources"] == ["ElDeber", "Unitel"]
    assert result["source_count"] == 2


def test_build_coverage_summary_treats_unknown_confidence_as_single_source():
    result = build_coverage_summary(sources=["Unitel"], claims=[_claim("algo-raro")])
    assert len(result["reported_by_single_source"]) == 1
    assert result["confirmed_by_multiple_sources"] == []


def test_build_coverage_summary_ignores_malformed_claim_entries():
    result = build_coverage_summary(sources=["Unitel"], claims=["not-a-dict", None, _claim("multi_source")])
    assert len(result["confirmed_by_multiple_sources"]) == 1


def test_build_coverage_summary_handles_no_claims_or_sources():
    result = build_coverage_summary(sources=[], claims=[])
    assert result == {
        "source_count": 0,
        "sources": [],
        "confirmed_by_multiple_sources": [],
        "based_on_official_statement": [],
        "reported_by_single_source": [],
    }
