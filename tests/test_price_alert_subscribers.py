"""Tests for PriceAlertSubscriberRepository, la lista de chats suscriptos a
las alertas de precio (tabla price_alert_subscribers) -- ver
src/notifiers/price_alert_notifier.py."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.price_alert_subscribers import PriceAlertSubscriberRepository
from src.db.repository import Base


@pytest.fixture
async def repository():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield PriceAlertSubscriberRepository(maker)
    await engine.dispose()


@pytest.mark.asyncio
async def test_not_subscribed_by_default(repository):
    assert await repository.is_subscribed("123456") is False
    assert await repository.list_chat_ids() == []


@pytest.mark.asyncio
async def test_add_then_is_subscribed(repository):
    await repository.add("123456")

    assert await repository.is_subscribed("123456") is True
    assert await repository.list_chat_ids() == ["123456"]


@pytest.mark.asyncio
async def test_add_is_idempotent(repository):
    await repository.add("123456")
    await repository.add("123456")

    assert await repository.list_chat_ids() == ["123456"]


@pytest.mark.asyncio
async def test_add_keeps_chats_independent(repository):
    await repository.add("111")
    await repository.add("222")

    assert await repository.list_chat_ids() == ["111", "222"]


@pytest.mark.asyncio
async def test_remove_then_not_subscribed(repository):
    await repository.add("123456")
    await repository.remove("123456")

    assert await repository.is_subscribed("123456") is False
    assert await repository.list_chat_ids() == []


@pytest.mark.asyncio
async def test_remove_missing_chat_is_a_no_op(repository):
    await repository.remove("123456")

    assert await repository.list_chat_ids() == []
