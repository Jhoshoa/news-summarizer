"""Tests for get_recent_article_details, the lookup the scraper uses to
decide which URLs it can reuse instead of re-fetching (see
tests/test_scraper_known_article_reuse.py for the scraper-side logic)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.repository import Base, Database, NewsArticle, NewsCategory, NewsSource


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


@pytest.mark.asyncio
async def test_get_recent_article_details_only_includes_articles_with_content(db: Database):
    async with db.session_maker() as session:
        category = NewsCategory(name="general", display_name="General")
        source = NewsSource(name="Fuente", source_type="scraper")
        session.add_all([category, source])
        await session.flush()

        now = datetime(2026, 8, 27, 12, 0, 0)
        session.add(NewsArticle(
            title="Con contenido",
            url="https://example.com/a",
            url_hash="hash-a",
            content="Contenido completo de la nota.",
            description="Descripcion",
            image_url="https://example.com/a.jpg",
            category_id=category.id,
            source_id=source.id,
            published_at=now,
            collected_at=now,
            is_active=True,
        ))
        session.add(NewsArticle(
            title="Sin contenido todavia",
            url="https://example.com/b",
            url_hash="hash-b",
            content=None,
            category_id=category.id,
            source_id=source.id,
            published_at=now,
            collected_at=now,
            is_active=True,
        ))
        await session.commit()

    details = await db.get_recent_article_details(since=now - timedelta(hours=1))

    assert set(details.keys()) == {"hash-a"}
    assert details["hash-a"]["content"] == "Contenido completo de la nota."
    assert details["hash-a"]["description"] == "Descripcion"
    assert details["hash-a"]["image"] == "https://example.com/a.jpg"
    assert details["hash-a"]["published_at"] == now


@pytest.mark.asyncio
async def test_get_recent_article_details_excludes_articles_older_than_since(db: Database):
    async with db.session_maker() as session:
        category = NewsCategory(name="general", display_name="General")
        source = NewsSource(name="Fuente", source_type="scraper")
        session.add_all([category, source])
        await session.flush()

        old = datetime(2026, 8, 20, 12, 0, 0)
        session.add(NewsArticle(
            title="Vieja",
            url="https://example.com/old",
            url_hash="hash-old",
            content="Contenido viejo.",
            category_id=category.id,
            source_id=source.id,
            published_at=old,
            collected_at=old,
            is_active=True,
        ))
        await session.commit()

    details = await db.get_recent_article_details(
        since=datetime(2026, 8, 27, 0, 0, 0)
    )

    assert details == {}
