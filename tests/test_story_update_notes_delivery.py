from types import SimpleNamespace
from unittest.mock import patch

import pytest
import sentry_sdk

from src.main import NewsSummarizerApp


def _make_app(db=None):
    settings = SimpleNamespace(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
    )
    app = NewsSummarizerApp(settings)
    app.db = db
    return app


class FakeNotesDatabase:
    def __init__(self, notes_by_cluster: dict):
        self.notes_by_cluster = notes_by_cluster
        self.calls: list[set] = []

    async def get_story_update_notes(self, story_cluster_ids):
        self.calls.append(set(story_cluster_ids))
        return {
            cid: note for cid, note in self.notes_by_cluster.items() if cid in story_cluster_ids
        }


class RaisingNotesDatabase:
    async def get_story_update_notes(self, story_cluster_ids):
        raise RuntimeError("db unavailable")


@pytest.mark.asyncio
async def test_attach_story_update_notes_adds_note_when_present():
    db = FakeNotesDatabase({"cluster-1": "Actualizacion: nuevos datos"})
    app = _make_app(db)
    summaries = [
        {"title": "A", "story_cluster_id": "cluster-1"},
        {"title": "B", "story_cluster_id": "cluster-2"},
    ]

    await app._attach_story_update_notes(summaries)

    assert summaries[0]["update_note"] == "Actualizacion: nuevos datos"
    assert "update_note" not in summaries[1]
    assert db.calls == [{"cluster-1", "cluster-2"}]


@pytest.mark.asyncio
async def test_attach_story_update_notes_skips_when_no_cluster_ids():
    db = FakeNotesDatabase({})
    app = _make_app(db)
    summaries = [{"title": "Sin cluster"}]

    await app._attach_story_update_notes(summaries)

    assert "update_note" not in summaries[0]
    assert db.calls == []


@pytest.mark.asyncio
async def test_attach_story_update_notes_degrades_gracefully_on_db_error():
    app = _make_app(RaisingNotesDatabase())
    summaries = [{"title": "A", "story_cluster_id": "cluster-1"}]

    await app._attach_story_update_notes(summaries)

    assert "update_note" not in summaries[0]


@pytest.mark.asyncio
async def test_attach_story_update_notes_reports_db_error_to_sentry():
    app = _make_app(RaisingNotesDatabase())
    summaries = [{"title": "A", "story_cluster_id": "cluster-1"}]

    with patch.object(sentry_sdk, "capture_exception") as mock_capture:
        await app._attach_story_update_notes(summaries)

    mock_capture.assert_called_once()
    assert isinstance(mock_capture.call_args.args[0], RuntimeError)


@pytest.mark.asyncio
async def test_attach_story_update_notes_noop_without_db():
    app = _make_app(db=None)
    summaries = [{"title": "A", "story_cluster_id": "cluster-1"}]

    await app._attach_story_update_notes(summaries)

    assert "update_note" not in summaries[0]


def test_format_summary_includes_update_note_when_present():
    app = _make_app()
    text = app._format_summary(
        [{"title": "Titulo", "summary": "Resumen", "update_note": "Actualizacion: cambio importante"}]
    )
    assert "Actualizacion: cambio importante" in text


def test_format_summary_omits_update_note_when_absent():
    app = _make_app()
    text = app._format_summary([{"title": "Titulo", "summary": "Resumen"}])
    assert "Actualizacion" not in text


def test_format_email_summary_includes_update_note_in_text_and_html():
    app = _make_app()
    _subject, body, html_body = app._format_email_summary(
        [
            {
                "title": "Titulo",
                "summary": "Resumen",
                "update_note": "Actualizacion: la medida fue suspendida",
            }
        ]
    )
    assert "Actualizacion: la medida fue suspendida" in body
    assert "Actualizacion: la medida fue suspendida" in html_body


def test_format_email_summary_escapes_update_note_html():
    app = _make_app()
    _subject, _body, html_body = app._format_email_summary(
        [{"title": "Titulo", "summary": "Resumen", "update_note": "1 < 2 & 3 > 0"}]
    )
    assert "1 &lt; 2 &amp; 3 &gt; 0" in html_body


def test_format_email_summary_omits_update_note_block_when_absent():
    app = _make_app()
    _subject, body, html_body = app._format_email_summary([{"title": "Titulo", "summary": "Resumen"}])
    assert "Actualizacion" not in body
    assert "border-left:3px solid #d97706" not in html_body
