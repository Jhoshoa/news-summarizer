"""Tests for TelegramLinkRepository, the one-use tokens behind the
`t.me/<bot>?start=<token>` deep link generated from the subscribe form so the
categories/frequency/hour chosen on the web are applied by the bot without
asking again (see src/distributors/telegram_handler.py::_handle_start_with_token)."""

from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.repository import Base, _now_bolivia
from src.db.telegram_links import TelegramLinkRepository, TelegramLinkToken


@pytest.fixture
async def session_maker():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_link_returns_url_safe_token_and_requested_ttl(session_maker):
    repo = TelegramLinkRepository(session_maker)

    token, ttl = await repo.create_link(
        categories={"economia", "deportes"},
        frequency="semanal",
        preferred_hour=20,
        timezone="America/La_Paz",
        consent_accepted=True,
        ttl_seconds=120,
    )

    assert ttl == 120
    assert token
    assert all(char.isalnum() or char in "-_" for char in token)


@pytest.mark.asyncio
async def test_consume_link_returns_preferences_and_marks_it_used(session_maker):
    repo = TelegramLinkRepository(session_maker)
    token, _ = await repo.create_link(
        categories={"economia", "deportes"},
        frequency="semanal",
        preferred_hour=20,
        timezone="America/La_Paz",
        consent_accepted=True,
    )

    preferences = await repo.consume_link(token)

    assert preferences == {
        "categories": ["deportes", "economia"],
        "frequency": "semanal",
        "preferred_hour": 20,
        "timezone": "America/La_Paz",
        "consent_accepted": True,
    }


@pytest.mark.asyncio
async def test_consume_link_returns_none_for_unknown_token(session_maker):
    repo = TelegramLinkRepository(session_maker)

    assert await repo.consume_link("no-existe") is None


@pytest.mark.asyncio
async def test_consume_link_returns_none_when_already_used(session_maker):
    repo = TelegramLinkRepository(session_maker)
    token, _ = await repo.create_link(
        categories={"general"},
        frequency="diario",
        preferred_hour=9,
        timezone="America/La_Paz",
        consent_accepted=True,
    )

    first = await repo.consume_link(token)
    second = await repo.consume_link(token)

    assert first is not None
    assert second is None


@pytest.mark.asyncio
async def test_consume_link_returns_none_when_expired(session_maker):
    async with session_maker() as session:
        now = _now_bolivia()
        session.add(
            TelegramLinkToken(
                token="ya-vencido",
                categories=["general"],
                frequency="diario",
                preferred_hour=9,
                timezone="America/La_Paz",
                consent_accepted=True,
                created_at=now - timedelta(seconds=700),
                expires_at=now - timedelta(seconds=100),
            )
        )
        await session.commit()

    repo = TelegramLinkRepository(session_maker)
    assert await repo.consume_link("ya-vencido") is None
