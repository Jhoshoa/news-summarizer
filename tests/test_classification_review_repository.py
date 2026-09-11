"""Tests for Database.get_articles_needing_category_review -- the query that
backs /admin/classification/review-queue. Same fake-session pattern as
tests/test_repository_category_queries.py: no real SQL engine, just a fake
AsyncSession that captures the statement and returns canned rows, so the
WHERE/ORDER BY and the Python-side raw_payload filter get exercised for
real.
"""

from datetime import datetime
from types import SimpleNamespace

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

    def first(self):
        return self._rows[0] if self._rows else None


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


def _fake_article(article_id: int, raw_payload: dict, category_id: int = 3) -> SimpleNamespace:
    return SimpleNamespace(
        id=article_id,
        category_id=category_id,
        title=f"Articulo {article_id}",
        url=f"https://example.com/{article_id}",
        description="desc",
        content=None,
        author=None,
        image_url=None,
        published_at=datetime(2026, 9, 9, 16, 0, 0),
        collected_at=datetime(2026, 9, 9, 19, 0, 0),
        country="bolivia",
        url_hash="hash",
        score=1.0,
        canonical_key=None,
        content_fingerprint=None,
        story_cluster_id=None,
        duplicate_of_article_id=None,
        duplicate_reason=None,
        similarity_score=None,
        raw_payload=raw_payload,
        is_active=True,
    )


def _row(article_id: int, raw_payload: dict):
    return (_fake_article(article_id, raw_payload), "deportes", "ElDeber", "scraper")


@pytest.mark.asyncio
async def test_filters_to_rules_low_confidence_and_llm_error_only():
    rows = [
        _row(1, {"category_method": "rules_low_confidence"}),
        _row(2, {"category_method": "rules", "category_llm_error": "invalid_category:x"}),
        _row(3, {"category_method": "rules"}),  # ni una ni otra senal -- no deberia salir
        _row(4, {"category_method": "llm_fallback"}),  # ya fue revisado y corregido por IA
    ]
    db, session = _database_with_session(rows)

    result = await db.get_articles_needing_category_review(180, limit=50)

    assert {a["id"] for a in result} == {1, 2}


@pytest.mark.asyncio
async def test_respects_the_limit_even_with_more_candidates_available():
    rows = [_row(i, {"category_method": "rules_low_confidence"}) for i in range(10)]
    db, session = _database_with_session(rows)

    result = await db.get_articles_needing_category_review(180, limit=3)

    assert len(result) == 3


@pytest.mark.asyncio
async def test_query_filters_by_is_active_and_orders_by_collected_at_desc():
    db, session = _database_with_session([])

    await db.get_articles_needing_category_review(180, limit=50)

    assert len(session.executed_statements) == 1
    sql = _compiled_sql(session.executed_statements[0])
    assert "is_active" in sql
    assert "ORDER BY" in sql
    assert "collected_at DESC" in sql


@pytest.mark.asyncio
async def test_handles_articles_with_no_raw_payload():
    rows = [_row(1, None)]
    db, _ = _database_with_session(rows)

    result = await db.get_articles_needing_category_review(180, limit=50)

    assert result == []


# --- correct_article_category: clears the review-queue signal after fixing ---


class _FakeCategory:
    def __init__(self, category_id: int, name: str):
        self.id = category_id
        self.name = name


class _FakeCorrectionSession:
    """Supports the subset of AsyncSession that correct_article_category
    uses: session.get (article + category lookup via _get_category's
    select), commit, refresh, and a final execute() for the joined re-read."""

    def __init__(self, article, category, final_row):
        self._article = article
        self._category = category
        self._final_row = final_row
        self.committed = False

    async def get(self, model, obj_id):
        return self._article

    async def execute(self, stmt):
        # _get_category's select(NewsCategory)... and the final joined
        # select both go through here; distinguish by whether it looks
        # like the NewsCategory-only lookup (has .scalar_one_or_none only
        # relevant for the category path) -- simplest: track call count.
        self._execute_calls = getattr(self, "_execute_calls", 0) + 1
        if self._execute_calls == 1:
            return SimpleNamespace(scalar_one_or_none=lambda: self._category)
        return _FakeResult([self._final_row])

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        return None


def _database_with_correction_session(article, category, final_row):
    db = object.__new__(Database)
    session = _FakeCorrectionSession(article, category, final_row)
    db.session_maker = lambda: _FakeSessionCtx(session)
    return db, session


@pytest.mark.asyncio
async def test_correct_article_category_clears_review_flags():
    article = _fake_article(5414, {"category_method": "rules_low_confidence", "category_llm_error": "x"})
    category = _FakeCategory(27, "policiales")
    final_row = _row(5414, {})  # el contenido exacto no importa para esta asercion

    db, session = _database_with_correction_session(article, category, final_row)

    await db.correct_article_category(5414, "policiales", reason="test", corrected_by="tester")

    assert session.committed is True
    assert article.category_id == 27
    assert article.raw_payload["category_method"] == "manual_correction"
    assert "category_llm_error" not in article.raw_payload
    assert article.raw_payload["category_manual_correction"]["reason"] == "test"


@pytest.mark.asyncio
async def test_correct_article_category_returns_none_for_inactive_article():
    article = _fake_article(1, {})
    article.is_active = False
    db, _ = _database_with_correction_session(article, _FakeCategory(1, "policiales"), None)

    result = await db.correct_article_category(1, "policiales", reason="test", corrected_by="tester")

    assert result is None


@pytest.mark.asyncio
async def test_correct_article_category_raises_for_unknown_category():
    article = _fake_article(1, {})
    db, _ = _database_with_correction_session(article, None, None)

    with pytest.raises(ValueError, match="Categoria desconocida"):
        await db.correct_article_category(1, "no-existe", reason="test", corrected_by="tester")
