"""Tests for PriceAlertRepository, el estado (una fila por indicator_code)
que PriceAlertNotifier usa como referencia "desde la ultima alerta" --
ver src/notifiers/price_alert_notifier.py."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.price_alerts import PriceAlertRepository
from src.db.repository import Base


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
async def test_get_reference_returns_none_when_never_set(session_maker):
    repo = PriceAlertRepository(session_maker)

    assert await repo.get_reference("binance_p2p_usdt_bob_buy") is None


@pytest.mark.asyncio
async def test_set_reference_then_get_returns_the_saved_value(session_maker):
    repo = PriceAlertRepository(session_maker)

    await repo.set_reference("binance_p2p_usdt_bob_buy", Decimal("12.20"))

    assert await repo.get_reference("binance_p2p_usdt_bob_buy") == Decimal("12.20")


@pytest.mark.asyncio
async def test_set_reference_overwrites_existing_value_for_same_code(session_maker):
    repo = PriceAlertRepository(session_maker)

    await repo.set_reference("binance_p2p_usdt_bob_buy", Decimal("12.20"))
    await repo.set_reference("binance_p2p_usdt_bob_buy", Decimal("12.50"))

    assert await repo.get_reference("binance_p2p_usdt_bob_buy") == Decimal("12.50")


@pytest.mark.asyncio
async def test_set_reference_keeps_codes_independent(session_maker):
    """Compra y venta tienen su propia referencia -- moverla en una no debe
    afectar a la otra."""

    repo = PriceAlertRepository(session_maker)

    await repo.set_reference("binance_p2p_usdt_bob_buy", Decimal("12.20"))
    await repo.set_reference("binance_p2p_usdt_bob_sell", Decimal("12.40"))

    assert await repo.get_reference("binance_p2p_usdt_bob_buy") == Decimal("12.20")
    assert await repo.get_reference("binance_p2p_usdt_bob_sell") == Decimal("12.40")


@pytest.mark.asyncio
async def test_get_reference_with_time_returns_none_when_never_set(session_maker):
    repo = PriceAlertRepository(session_maker)

    assert await repo.get_reference_with_time("binance_p2p_usdt_bob_buy") is None


@pytest.mark.asyncio
async def test_set_reference_stores_collected_at_with_value(session_maker):
    repo = PriceAlertRepository(session_maker)
    ts = datetime(2026, 9, 22, 11, 32)

    await repo.set_reference("binance_p2p_usdt_bob_buy", Decimal("12.20"), collected_at=ts)

    assert await repo.get_reference_with_time("binance_p2p_usdt_bob_buy") == (
        Decimal("12.20"),
        ts,
    )


@pytest.mark.asyncio
async def test_set_reference_without_collected_at_stores_none(session_maker):
    """Filas previas a la migracion 023 o valores sin hora: la referencia se
    guarda igual, solo que sin timestamp (el aviso se arma sin hora)."""

    repo = PriceAlertRepository(session_maker)

    await repo.set_reference("binance_p2p_usdt_bob_buy", Decimal("12.20"))

    assert await repo.get_reference_with_time("binance_p2p_usdt_bob_buy") == (
        Decimal("12.20"),
        None,
    )


@pytest.mark.asyncio
async def test_set_reference_overwrite_updates_collected_at(session_maker):
    repo = PriceAlertRepository(session_maker)
    await repo.set_reference(
        "binance_p2p_usdt_bob_buy",
        Decimal("12.20"),
        collected_at=datetime(2026, 9, 22, 11, 32),
    )

    await repo.set_reference(
        "binance_p2p_usdt_bob_buy",
        Decimal("12.50"),
        collected_at=datetime(2026, 9, 22, 11, 35),
    )

    assert await repo.get_reference_with_time("binance_p2p_usdt_bob_buy") == (
        Decimal("12.50"),
        datetime(2026, 9, 22, 11, 35),
    )
