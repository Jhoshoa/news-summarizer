"""Tests for the category-related SQL query building in src/db/repository.py.

These exercise the real query-construction and result-processing logic (not a
fake in-memory database), by handing the repository a fake AsyncSession that
captures whatever statement it's asked to execute and returns canned rows.
This project has no fixture for a real SQL engine in tests, so asserting on
the compiled SQL text is how we catch a wrong JOIN/WHERE/GROUP BY without
introducing a new test dependency.
"""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.db.repository import Database


class _FakeSessionCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc_info):
        return False


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.executed_statements = []

    async def execute(self, stmt):
        self.executed_statements.append(stmt)
        return _FakeResult(self._rows)


def _compiled_sql(stmt) -> str:
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


def _database_with_session(rows) -> tuple[Database, _FakeSession]:
    db = object.__new__(Database)
    session = _FakeSession(rows)
    db.session_maker = lambda: _FakeSessionCtx(session)
    return db, session


# --- get_preference_preview: excludes unpublished stories (fix in b4e83dd) ---


@pytest.mark.asyncio
async def test_get_preference_preview_sql_excludes_unpublished_stories():
    db, session = _database_with_session(rows=[])

    await db.get_preference_preview(["economia"])

    assert len(session.executed_statements) == 1
    sql = _compiled_sql(session.executed_statements[0])
    assert "LEFT OUTER JOIN stories" in sql
    assert "stories.current_status != 'unpublished'" in sql
    assert "stories.id IS NULL" in sql


@pytest.mark.asyncio
async def test_get_preference_preview_filters_by_normalized_categories_only():
    db, session = _database_with_session(rows=[])

    await db.get_preference_preview(["economia", "no-existe", "policiales"])

    sql = _compiled_sql(session.executed_statements[0])
    assert "'economia'" in sql
    assert "'policiales'" in sql
    assert "'no-existe'" not in sql


@pytest.mark.asyncio
async def test_get_preference_preview_returns_empty_list_without_querying_when_no_valid_category():
    db, session = _database_with_session(rows=[])

    items = await db.get_preference_preview(["no-existe"])

    assert items == []
    assert session.executed_statements == []


@pytest.mark.asyncio
async def test_get_preference_preview_deduplicates_by_normalized_title():
    from datetime import date as date_cls
    from types import SimpleNamespace

    duplicate_a = SimpleNamespace(
        title="Suben precios del combustible",
        summary="resumen A",
        fact=None,
        summary_date=date_cls(2026, 8, 25),
    )
    duplicate_b = SimpleNamespace(
        title="SUBEN PRECIOS DEL COMBUSTIBLE",
        summary="resumen B (mismo titulo, distinta mayuscula)",
        fact=None,
        summary_date=date_cls(2026, 8, 25),
    )
    distinct = SimpleNamespace(
        title="Otra noticia distinta",
        summary="resumen C",
        fact=None,
        summary_date=date_cls(2026, 8, 25),
    )
    rows = [
        (duplicate_a, "economia"),
        (duplicate_b, "economia"),
        (distinct, "economia"),
    ]
    db, _ = _database_with_session(rows=rows)

    items = await db.get_preference_preview(["economia"], limit=5)

    assert len(items) == 2
    assert items[0]["title"] == "Suben precios del combustible"
    assert items[1]["title"] == "Otra noticia distinta"


# --- _category_counts_for: correct filters/group-by per view ---


@pytest.mark.asyncio
async def test_category_counts_for_recolectadas_filters_active_articles_by_day_and_groups_by_category():
    db, session = _database_with_session(rows=[("economia", 3), ("deportes", 1)])

    counts, total = await db._category_counts_for(session, "recolectadas", date(2026, 8, 25))

    assert counts == {"economia": 3, "deportes": 1}
    assert total == 4
    sql = _compiled_sql(session.executed_statements[0])
    assert "news_articles" in sql
    assert "news_articles.is_active IS true" in sql
    assert "news_articles.published_at >= '2026-08-25 00:00:00'" in sql
    assert "news_articles.published_at < '2026-08-26 00:00:00'" in sql
    assert "GROUP BY news_categories.name" in sql


@pytest.mark.asyncio
async def test_category_counts_for_resumenes_filters_by_exact_summary_date_and_groups_by_category():
    db, session = _database_with_session(rows=[("economia", 2)])

    counts, total = await db._category_counts_for(session, "resumenes", date(2026, 8, 25))

    assert counts == {"economia": 2}
    assert total == 2
    sql = _compiled_sql(session.executed_statements[0])
    assert "news_summaries" in sql
    assert "news_summaries.summary_date = '2026-08-25'" in sql
    assert "GROUP BY news_categories.name" in sql


@pytest.mark.asyncio
async def test_category_counts_for_returns_zero_total_with_no_rows():
    db, session = _database_with_session(rows=[])

    counts, total = await db._category_counts_for(session, "resumenes", date(2026, 8, 25))

    assert counts == {}
    assert total == 0


# --- get_category_counts: fallback-to-latest orchestration ---


@pytest.mark.asyncio
async def test_get_category_counts_does_not_fall_back_when_data_exists():
    db, session = _database_with_session(rows=[("economia", 1)])
    db._latest_summary_date = AsyncMock()

    result = await db.get_category_counts(
        view="resumenes", target_date=date(2026, 8, 25), fallback_to_latest=True
    )

    assert result["is_fallback"] is False
    assert result["date"] == date(2026, 8, 25)
    db._latest_summary_date.assert_not_called()
    assert len(session.executed_statements) == 1


@pytest.mark.asyncio
async def test_get_category_counts_falls_back_to_latest_available_date_when_empty():
    db, session = _database_with_session(rows=[])
    db._latest_summary_date = AsyncMock(return_value=date(2026, 8, 20))

    async def fake_category_counts_for(session_, view, target_date):
        if target_date == date(2026, 8, 20):
            return {"economia": 5}, 5
        return {}, 0

    db._category_counts_for = fake_category_counts_for

    result = await db.get_category_counts(
        view="resumenes", target_date=date(2026, 8, 25), fallback_to_latest=True
    )

    assert result["is_fallback"] is True
    assert result["date"] == date(2026, 8, 20)
    assert result["requested_date"] == date(2026, 8, 25)
    assert result["total"] == 5
    assert result["counts"] == {"economia": 5}


@pytest.mark.asyncio
async def test_get_category_counts_does_not_fall_back_without_the_flag():
    db, session = _database_with_session(rows=[])
    db._latest_summary_date = AsyncMock(return_value=date(2026, 8, 20))

    result = await db.get_category_counts(
        view="resumenes", target_date=date(2026, 8, 25), fallback_to_latest=False
    )

    assert result["is_fallback"] is False
    assert result["date"] == date(2026, 8, 25)
    db._latest_summary_date.assert_not_called()


@pytest.mark.asyncio
async def test_get_category_counts_uses_latest_article_date_for_recolectadas_view():
    db, session = _database_with_session(rows=[])
    db._latest_article_date = AsyncMock(return_value=date(2026, 8, 19))
    db._latest_summary_date = AsyncMock(return_value=date(2026, 8, 20))

    async def fake_category_counts_for(session_, view, target_date):
        return ({"policiales": 2}, 2) if target_date == date(2026, 8, 19) else ({}, 0)

    db._category_counts_for = fake_category_counts_for

    result = await db.get_category_counts(
        view="recolectadas", target_date=date(2026, 8, 25), fallback_to_latest=True
    )

    db._latest_article_date.assert_called_once()
    db._latest_summary_date.assert_not_called()
    assert result["date"] == date(2026, 8, 19)
    assert result["counts"] == {"policiales": 2}
