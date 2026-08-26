"""Tests for excluding unpublished stories from the public article/summary feeds.

Before this fix, only list_stories() and get_preference_preview() respected
Story.current_status == "unpublished" -- the moderation flag set by
set_story_publication_status(). list_summaries() and list_articles(), which
back the main /news page everyone reads, ignored it entirely: correcting or
retracting a story didn't actually hide it from the public feed.

Same testing approach as test_repository_category_queries.py: a fake
AsyncSession captures the compiled statement so we can assert on the real
SQL without a live database fixture.
"""

from datetime import date

import pytest

from src.db.repository import Database


def _compiled_sql(stmt) -> str:
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


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
    """Supports both session.scalar(stmt) (used for the count query) and
    session.execute(stmt) (used for the row listing), like list_articles/
    list_summaries actually call them."""

    def __init__(self, scalar_value=0, rows=None):
        self.scalar_value = scalar_value
        self.rows = rows or []
        self.executed_statements = []

    async def scalar(self, stmt):
        self.executed_statements.append(stmt)
        return self.scalar_value

    async def execute(self, stmt):
        self.executed_statements.append(stmt)
        return _FakeResult(self.rows)


def _database_with_session(scalar_value=0, rows=None) -> tuple[Database, _FakeSession]:
    db = object.__new__(Database)
    session = _FakeSession(scalar_value=scalar_value, rows=rows)
    db.session_maker = lambda: _FakeSessionCtx(session)
    return db, session


# --- the filter clauses themselves, in isolation ---


def test_article_not_unpublished_filter_excludes_via_story_articles_join():
    db = object.__new__(Database)

    clause = db._article_not_unpublished_filter()

    sql = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert sql.startswith("NOT (EXISTS")
    assert "story_articles" in sql
    assert "story_articles.article_id = news_articles.id" in sql
    assert "stories.current_status = 'unpublished'" in sql


def test_summary_not_unpublished_filter_excludes_via_story_cluster_id():
    db = object.__new__(Database)

    clause = db._summary_not_unpublished_filter()

    sql = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert sql.startswith("NOT (EXISTS")
    assert "stories.id = news_summaries.story_cluster_id" in sql
    assert "stories.current_status = 'unpublished'" in sql


# --- list_articles: the filter actually reaches both queries ---


@pytest.mark.asyncio
async def test_list_articles_excludes_unpublished_in_both_count_and_listing_queries():
    db, session = _database_with_session(scalar_value=0, rows=[])

    await db.list_articles(article_date=date(2026, 8, 25))

    assert len(session.executed_statements) == 2
    for stmt in session.executed_statements:
        sql = _compiled_sql(stmt)
        assert "story_articles" in sql
        assert "'unpublished'" in sql


@pytest.mark.asyncio
async def test_list_articles_fallback_path_also_excludes_unpublished():
    """total_stmt is rebuilt when falling back to the latest available date --
    that rebuilt statement must carry the filter too, not just the first one."""

    db, session = _database_with_session(scalar_value=0, rows=[])
    db._latest_article_date = lambda *a, **k: _AwaitableDate(date(2026, 8, 20))

    await db.list_articles(article_date=date(2026, 8, 25), fallback_to_latest=True)

    # count query (empty) -> _latest_article_date -> rebuilt count query -> listing query
    assert len(session.executed_statements) >= 2
    for stmt in session.executed_statements:
        sql = _compiled_sql(stmt)
        assert "story_articles" in sql


class _AwaitableDate:
    def __init__(self, value):
        self.value = value

    def __await__(self):
        async def _coro():
            return self.value

        return _coro().__await__()


# --- list_summaries: the filter actually reaches both queries ---


@pytest.mark.asyncio
async def test_list_summaries_excludes_unpublished_in_both_count_and_listing_queries():
    db, session = _database_with_session(scalar_value=0, rows=[])

    await db.list_summaries(summary_date=date(2026, 8, 25))

    assert len(session.executed_statements) == 2
    for stmt in session.executed_statements:
        sql = _compiled_sql(stmt)
        assert "stories" in sql
        assert "'unpublished'" in sql


# --- _category_counts_for: both views exclude unpublished too ---


@pytest.mark.asyncio
async def test_category_counts_for_recolectadas_excludes_unpublished():
    db, session = _database_with_session(rows=[])

    await db._category_counts_for(session, "recolectadas", date(2026, 8, 25))

    sql = _compiled_sql(session.executed_statements[0])
    assert "story_articles" in sql
    assert "'unpublished'" in sql


@pytest.mark.asyncio
async def test_category_counts_for_resumenes_excludes_unpublished():
    db, session = _database_with_session(rows=[])

    await db._category_counts_for(session, "resumenes", date(2026, 8, 25))

    sql = _compiled_sql(session.executed_statements[0])
    assert "stories" in sql
    assert "'unpublished'" in sql


# --- no row-duplication risk: EXISTS, not a JOIN that could fan out rows ---


def test_unpublished_filters_use_exists_not_a_join():
    """A regression test for the exact bug the user asked about: fixing this
    with a plain JOIN against story_articles (an article can have more than
    one row there) would silently duplicate rows in the results and break
    pagination totals. EXISTS is a scalar boolean subquery -- it can never
    multiply rows, regardless of how many stories an article is linked to."""

    db = object.__new__(Database)

    article_clause_sql = str(
        db._article_not_unpublished_filter().compile(compile_kwargs={"literal_binds": True})
    )
    summary_clause_sql = str(
        db._summary_not_unpublished_filter().compile(compile_kwargs={"literal_binds": True})
    )

    assert article_clause_sql.strip().startswith("NOT (EXISTS")
    assert summary_clause_sql.strip().startswith("NOT (EXISTS")
