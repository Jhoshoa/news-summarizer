"""Tests for the "varias fuentes" badge data: list_articles/list_summaries now
expose source_count (from the article's Story cluster) so the frontend can
show a small badge on NewsCard/SummaryCard when 2+ outlets cover the same
story, without an extra query per item and without repeating the request the
detail page's trust panel already makes.
"""

from datetime import date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.repository import (
    Base,
    Database,
    NewsArticle,
    NewsCategory,
    NewsSource,
    NewsSummary,
    Story,
)


@pytest.fixture
async def db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    database = object.__new__(Database)
    database.engine = engine
    database.session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield database
    await engine.dispose()


async def _seed_category_and_source(session, *, category_name="general", source_name="Fuente"):
    category = NewsCategory(name=category_name, display_name=category_name.capitalize())
    source = NewsSource(name=source_name, source_type="scraper")
    session.add_all([category, source])
    await session.flush()
    return category, source


async def _make_article(
    session, *, category_id, source_id, title, url, story_cluster_id, published_at
) -> NewsArticle:
    article = NewsArticle(
        title=title,
        url=url,
        url_hash=url,
        canonical_key=title,
        content_fingerprint=f"fp-{url}",
        story_cluster_id=story_cluster_id,
        category_id=category_id,
        source_id=source_id,
        published_at=published_at,
        collected_at=published_at,
        is_active=True,
    )
    session.add(article)
    await session.flush()
    return article


@pytest.mark.asyncio
async def test_list_articles_marks_multi_source_stories(db: Database):
    async with db.session_maker() as session:
        category, source_a = await _seed_category_and_source(session, source_name="RedUno")
        source_b = NewsSource(name="Unitel", source_type="scraper")
        session.add(source_b)
        await session.flush()

        now = datetime(2026, 8, 27, 12, 0, 0)
        await _make_article(
            session, category_id=category.id, source_id=source_a.id,
            title="Historia con dos fuentes", url="https://example.com/multi-1",
            story_cluster_id="cluster-multi", published_at=now,
        )
        await _make_article(
            session, category_id=category.id, source_id=source_b.id,
            title="Historia con dos fuentes (Unitel)", url="https://example.com/multi-2",
            story_cluster_id="cluster-multi", published_at=now,
        )
        await _make_article(
            session, category_id=category.id, source_id=source_a.id,
            title="Historia con una sola fuente", url="https://example.com/single-1",
            story_cluster_id="cluster-single", published_at=now,
        )
        session.add(Story(
            id="cluster-multi", canonical_title="Historia con dos fuentes", category="general",
            country="BO", first_published_at=now, last_updated_at=now,
            article_count=2, source_count=2,
        ))
        session.add(Story(
            id="cluster-single", canonical_title="Historia con una sola fuente", category="general",
            country="BO", first_published_at=now, last_updated_at=now,
            article_count=1, source_count=1,
        ))
        await session.commit()

    result = await db.list_articles(article_date=date(2026, 8, 27), page_size=10)

    by_title = {item["title"]: item["source_count"] for item in result["items"]}
    assert by_title["Historia con dos fuentes"] == 2
    assert by_title["Historia con dos fuentes (Unitel)"] == 2
    assert by_title["Historia con una sola fuente"] == 1


@pytest.mark.asyncio
async def test_list_articles_defaults_source_count_without_cluster(db: Database):
    async with db.session_maker() as session:
        category, source = await _seed_category_and_source(session)
        now = datetime(2026, 8, 27, 12, 0, 0)
        article = NewsArticle(
            title="Articulo sin cluster",
            url="https://example.com/no-cluster",
            url_hash="https://example.com/no-cluster",
            category_id=category.id,
            source_id=source.id,
            published_at=now,
            collected_at=now,
            is_active=True,
        )
        session.add(article)
        await session.commit()

    result = await db.list_articles(article_date=date(2026, 8, 27), page_size=10)

    assert result["items"][0]["source_count"] == 1


@pytest.mark.asyncio
async def test_list_summaries_marks_multi_source_stories(db: Database):
    async with db.session_maker() as session:
        category, source = await _seed_category_and_source(session)
        now = datetime(2026, 8, 27, 12, 0, 0)
        session.add(Story(
            id="cluster-multi", canonical_title="T", category="general",
            country="BO", first_published_at=now, last_updated_at=now,
            article_count=2, source_count=2,
        ))
        session.add(NewsSummary(
            category_id=category.id,
            story_cluster_id="cluster-multi",
            title="Resumen de historia con dos fuentes",
            summary="Resumen valido.",
            summary_date=date(2026, 8, 27),
            created_at=now,
        ))
        session.add(NewsSummary(
            category_id=category.id,
            story_cluster_id=None,
            title="Resumen de historia sin cluster",
            summary="Resumen valido.",
            summary_date=date(2026, 8, 27),
            created_at=now,
        ))
        await session.commit()

    result = await db.list_summaries(summary_date=date(2026, 8, 27), page_size=10)

    by_title = {item["title"]: item["source_count"] for item in result["items"]}
    assert by_title["Resumen de historia con dos fuentes"] == 2
    assert by_title["Resumen de historia sin cluster"] == 1
