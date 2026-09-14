"""Tests for Database.get_subscriber_by_telegram_id, the lookup the bot's
/noticias command uses to find a chat's saved categories without asking
again (see src/distributors/telegram_handler.py::_handle_on_demand_news)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.repository import Base, Database


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
async def test_get_subscriber_by_telegram_id_returns_saved_categories(db: Database):
    await db.save_subscription(
        telegram_id="555",
        channel="telegram",
        categories={"deportes", "tecnologia"},
        consent_accepted=True,
    )

    result = await db.get_subscriber_by_telegram_id("555")

    assert result["frequency"] == "diario"
    assert result["preferred_hour"] == 9
    assert sorted(result["categories"]) == ["deportes", "tecnologia"]


@pytest.mark.asyncio
async def test_get_subscriber_by_telegram_id_returns_none_for_unknown_chat(db: Database):
    assert await db.get_subscriber_by_telegram_id("no-existe") is None


@pytest.mark.asyncio
async def test_get_subscriber_by_telegram_id_ignores_unsubscribed_chats(db: Database):
    await db.save_subscription(
        telegram_id="555",
        channel="telegram",
        categories={"deportes"},
        consent_accepted=True,
    )
    await db.unsubscribe("555")

    assert await db.get_subscriber_by_telegram_id("555") is None
