from datetime import date, datetime
from types import SimpleNamespace

from src.db.repository import Database


def test_normalize_payload_serializes_datetime_values_recursively():
    db = object.__new__(Database)

    payload = db._normalize_payload(
        {
            "published_at": datetime(2026, 5, 10, 12, 30),
            "content_collected_at": datetime(2026, 5, 10, 12, 31),
            "metadata": {
                "seen_on": date(2026, 5, 10),
                "snapshots": [datetime(2026, 5, 10, 12, 32)],
            },
        }
    )

    assert payload == {
        "published_at": "2026-05-10T12:30:00",
        "content_collected_at": "2026-05-10T12:31:00",
        "metadata": {
            "seen_on": "2026-05-10",
            "snapshots": ["2026-05-10T12:32:00"],
        },
    }


def test_summary_row_to_dict_includes_joined_article_source_and_url():
    db = object.__new__(Database)
    summary = SimpleNamespace(
        id=1,
        article_id=123,
        title="Resumen",
        summary="Texto resumido",
        fact="Dato",
        llm_provider="groq",
        llm_model="model",
        summary_date=date(2026, 5, 10),
        created_at=datetime(2026, 5, 10, 12, 0),
    )

    row = (
        summary,
        "politica",
        "https://example.com/noticia",
        "Titulo original",
        "Example News",
    )

    result = db._summary_row_to_dict(row)

    assert result["article_id"] == 123
    assert result["source"] == "Example News"
    assert result["url"] == "https://example.com/noticia"
    assert result["article_title"] == "Titulo original"


def test_coerce_score_preserves_float_values():
    db = object.__new__(Database)

    assert db._coerce_score("0.885") == 0.885
    assert db._coerce_score(0.72) == 0.72
    assert db._coerce_score(None) == 0.0
    assert db._coerce_score("not-a-number") == 0.0


def test_article_row_to_dict_preserves_float_score():
    db = object.__new__(Database)
    article = SimpleNamespace(
        id=1,
        title="Titulo",
        url="https://example.com",
        description=None,
        content=None,
        author=None,
        image_url=None,
        published_at=datetime(2026, 5, 10, 12, 0),
        collected_at=datetime(2026, 5, 10, 12, 1),
        country="bolivia",
        url_hash="abc",
        score=0.885,
        canonical_key="politica | titulo",
        content_fingerprint="fingerprint",
        story_cluster_id="story-1",
        duplicate_of_article_id=10,
        duplicate_reason="fingerprint",
        similarity_score=1.0,
        raw_payload={"score": 0.885},
    )

    result = db._article_row_to_dict((article, "politica", "Example", "scraper"))

    assert result["score"] == 0.885
    assert result["story_cluster_id"] == "story-1"
    assert result["duplicate_of_article_id"] == 10
    assert result["duplicate_reason"] == "fingerprint"
    assert result["similarity_score"] == 1.0
    assert result["raw_payload"]["score"] == 0.885


def test_article_row_to_dict_hides_content_that_duplicates_description():
    db = object.__new__(Database)
    article = SimpleNamespace(
        id=1,
        title="Titulo",
        url="https://example.com",
        description="La entradilla de la noticia con datos principales.",
        content=" La entradilla de la noticia con datos principales. ",
        author=None,
        image_url=None,
        published_at=datetime(2026, 5, 10, 12, 0),
        collected_at=datetime(2026, 5, 10, 12, 1),
        country="bolivia",
        url_hash="abc",
        score=0.885,
        raw_payload={},
    )

    result = db._article_row_to_dict((article, "politica", "Example", "scraper"))

    assert result["description"] == "La entradilla de la noticia con datos principales."
    assert result["content"] is None


def test_day_bounds_cover_exact_selected_date():
    db = object.__new__(Database)

    start_at, end_at = db._day_bounds(date(2026, 5, 28))

    assert start_at == datetime(2026, 5, 28, 0, 0, 0)
    assert end_at == datetime(2026, 5, 29, 0, 0, 0)


def test_existing_scraper_article_keeps_original_published_at_when_new_date_is_fallback():
    db = object.__new__(Database)
    existing_published_at = datetime(2026, 6, 10, 8, 42)

    assert (
        db._should_update_article_published_at(
            {
                "source_type": "scraper",
                "published_at": datetime(2026, 6, 11, 9, 15),
                "published_at_from_listing": False,
            },
            existing_published_at,
        )
        is False
    )
    assert (
        db._should_update_article_published_at(
            {
                "source_type": "scraper",
                "published_at": datetime(2026, 6, 10, 8, 42),
                "published_at_from_detail": True,
            },
            existing_published_at,
        )
        is True
    )


def test_article_filters_can_exclude_summarized_articles_for_selected_date():
    db = object.__new__(Database)

    filters = db._article_filters(
        article_date=date(2026, 6, 3),
        exclude_summarized=True,
    )
    compiled_filter = str(filters[-1].compile(compile_kwargs={"literal_binds": True}))

    assert "NOT" in compiled_filter
    assert "news_summaries" in compiled_filter
    assert "news_summaries.article_id = news_articles.id" in compiled_filter
    assert "news_summaries.summary_date = '2026-06-03'" in compiled_filter


def test_summary_filters_keep_summary_date_aligned_with_article_publish_date():
    db = object.__new__(Database)

    filters = db._summary_filters(summary_date=date(2026, 6, 11))
    compiled_filters = "\n".join(
        str(item.compile(compile_kwargs={"literal_binds": True})) for item in filters
    )

    assert "news_summaries.summary_date = '2026-06-11'" in compiled_filters
    assert "date(news_articles.published_at) = '2026-06-11'" in compiled_filters


def test_paginated_response_includes_fallback_metadata():
    db = object.__new__(Database)

    response = db._paginated_response(
        items=[],
        total=0,
        page=1,
        page_size=20,
        date=date(2026, 5, 30),
        requested_date=date(2026, 5, 31),
        is_fallback=True,
    )

    assert response["date"] == date(2026, 5, 30)
    assert response["requested_date"] == date(2026, 5, 31)
    assert response["is_fallback"] is True


def test_build_impact_metrics_payload_calculates_transparent_estimates():
    db = object.__new__(Database)

    response = db._build_impact_metrics_payload(
        effective_date=date(2026, 6, 3),
        requested_date=date(2026, 6, 3),
        is_fallback=False,
        collected_articles=86,
        unique_articles=42,
        summaries=18,
        has_data=True,
    )

    assert response["has_data"] is True
    assert response["duplicate_articles_estimated"] == 44
    assert response["estimated_pages_avoided"] == 68
    assert response["estimated_minutes_saved"] == 34.0
    assert response["estimated_data_saved_mb"] == 54.4
    assert response["reduction_rate"] == 0.7907
    assert response["ai_calls_avoided_estimated"] == 44
    assert response["pipeline"] == [
        {"label": "Recolectadas", "value": 86},
        {"label": "Unicas", "value": 42},
        {"label": "Briefs", "value": 18},
    ]
    assert "no medicion energetica directa" in response["methodology"]["note"]


def test_build_impact_metrics_payload_includes_real_pipeline_fields():
    db = object.__new__(Database)

    response = db._build_impact_metrics_payload(
        effective_date=date(2026, 6, 3),
        requested_date=date(2026, 6, 3),
        is_fallback=False,
        data_source="pipeline_run",
        collected_articles=12,
        unique_articles=8,
        summaries=3,
        quality_dropped_articles=2,
        duplicate_articles=2,
        summary_candidates=5,
        usable_articles=10,
        ranked_articles=8,
        cache_reused=True,
        has_data=True,
    )

    assert response["data_source"] == "pipeline_run"
    assert response["quality_dropped_articles"] == 2
    assert response["duplicate_articles"] == 2
    assert response["duplicate_articles_estimated"] == 2
    assert response["summary_candidates"] == 5
    assert response["usable_articles"] == 10
    assert response["ranked_articles"] == 8
    assert response["cache_reused"] is True


def test_impact_summary_count_prefers_stored_daily_total_over_latest_run_count():
    db = object.__new__(Database)

    assert db._impact_summary_count(stored_summaries=28, run_summaries=5) == 28
    assert db._impact_summary_count(stored_summaries=0, run_summaries=5) == 5


def test_build_impact_metrics_payload_handles_empty_data_without_division_by_zero():
    db = object.__new__(Database)

    response = db._build_impact_metrics_payload(
        effective_date=date(2026, 6, 3),
        requested_date=date(2026, 6, 4),
        is_fallback=True,
        collected_articles=0,
        unique_articles=0,
        summaries=0,
        has_data=False,
    )

    assert response["has_data"] is False
    assert response["is_fallback"] is True
    assert response["reduction_rate"] == 0.0
    assert response["estimated_pages_avoided"] == 0
    assert response["estimated_minutes_saved"] == 0.0


def test_summary_title_key_normalizes_duplicate_titles():
    db = object.__new__(Database)

    assert db._summary_title_key("Video: Reportera cae al intentar atrapar regalo") == (
        db._summary_title_key(" video reportera cae al intentar atrapar regalo ")
    )


def test_summary_story_key_prefers_cluster_over_title():
    db = object.__new__(Database)

    assert db._summary_story_key(
        {
            "story_cluster_id": "cluster-1",
            "title": "Titulo cualquiera",
        }
    ) == "cluster:cluster-1"
    assert db._summary_story_key({"title": "Video: Titulo"}) == "title:video titulo"
