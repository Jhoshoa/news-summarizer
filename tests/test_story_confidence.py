from src.processors.story_confidence import classify_story_confidence


def test_multi_source_when_two_or_more_sources():
    result = classify_story_confidence(source_count=2, article_count=3, current_status="developing")
    assert result == {"level": "multi_source", "label": "Confirmado por varias fuentes"}


def test_single_source_when_exactly_one_article_one_source():
    result = classify_story_confidence(source_count=1, article_count=1, current_status="developing")
    assert result == {"level": "single_source", "label": "Reportado por una sola fuente"}


def test_developing_when_single_source_but_multiple_articles():
    result = classify_story_confidence(source_count=1, article_count=3, current_status="developing")
    assert result["level"] == "developing"


def test_official_statement_takes_priority_over_source_count():
    result = classify_story_confidence(
        source_count=1,
        article_count=1,
        current_status="developing",
        relationship_types=["original_report", "official_statement"],
    )
    assert result["level"] == "official_statement"


def test_corrected_status_takes_priority_over_everything():
    result = classify_story_confidence(
        source_count=5,
        article_count=6,
        current_status="corrected",
        relationship_types=["official_statement"],
    )
    assert result["level"] == "corrected"


def test_contradictory_status_takes_priority_over_source_count():
    result = classify_story_confidence(source_count=3, article_count=3, current_status="contradictory")
    assert result["level"] == "contradictory"


def test_unknown_status_falls_back_to_source_based_classification():
    result = classify_story_confidence(source_count=2, article_count=2, current_status="")
    assert result["level"] == "multi_source"
