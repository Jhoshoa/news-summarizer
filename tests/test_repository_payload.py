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
