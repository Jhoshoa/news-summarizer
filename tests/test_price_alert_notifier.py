"""Tests for PriceAlertNotifier: avisa por Telegram cuando compra/venta P2P
se mueve mas de un umbral desde la ULTIMA ALERTA (no desde la corrida
anterior, sin reset por dia) -- ver src/notifiers/price_alert_notifier.py
para el razonamiento completo detras de este diseno."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.price_alerts import PriceAlertRepository
from src.db.repository import Base
from src.notifiers.price_alert_notifier import PriceAlertNotifier

BUY = "binance_p2p_usdt_bob_buy"
SELL = "binance_p2p_usdt_bob_sell"


def _settings(
    token: str | None = "fake-token",
    chat_id: str | None = "123456",
    threshold: float = 1.0,
):
    return SimpleNamespace(
        price_alert_bot_token=token,
        price_alert_chat_id=chat_id,
        price_alert_threshold_percent=threshold,
    )


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


@pytest.fixture
async def repository(session_maker):
    yield PriceAlertRepository(session_maker)


def _items(buy=None, sell=None) -> list[dict]:
    items = []
    if buy is not None:
        items.append({"indicator_code": BUY, "value": buy})
    if sell is not None:
        items.append({"indicator_code": SELL, "value": sell})
    return items


@pytest.mark.asyncio
async def test_first_observation_sets_baseline_without_alerting(repository):
    notifier = PriceAlertNotifier(_settings(), repository)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(buy=12.20))

    mock_send.assert_not_awaited()
    assert await repository.get_reference(BUY) == Decimal("12.20")


@pytest.mark.asyncio
async def test_alerts_when_move_meets_or_exceeds_threshold(repository):
    notifier = PriceAlertNotifier(_settings(threshold=1.0), repository)
    await repository.set_reference(BUY, Decimal("12.00"))

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        # 12.00 -> 12.12 es +1.00% exacto -- el umbral es "igual o mayor", no
        # estrictamente mayor.
        await notifier.check_and_notify(_items(buy=12.12))

    mock_send.assert_awaited_once()
    kwargs = mock_send.call_args.kwargs
    assert kwargs["chat_id"] == "123456"
    assert "subio 1.00%" in kwargs["text"]
    assert await repository.get_reference(BUY) == Decimal("12.12")


@pytest.mark.asyncio
async def test_does_not_alert_when_move_is_under_threshold(repository):
    notifier = PriceAlertNotifier(_settings(threshold=1.0), repository)
    await repository.set_reference(BUY, Decimal("12.00"))

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(buy=12.05))  # +0.42%

    mock_send.assert_not_awaited()
    # La referencia NO se mueve si no hubo alerta -- el proximo chequeo debe
    # seguir comparando contra el mismo punto de partida (12.00), no contra
    # este ultimo valor visto (12.05).
    assert await repository.get_reference(BUY) == Decimal("12.00")


@pytest.mark.asyncio
async def test_downward_move_also_triggers_alert_with_correct_wording(repository):
    notifier = PriceAlertNotifier(_settings(threshold=1.0), repository)
    await repository.set_reference(SELL, Decimal("12.40"))

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(sell=12.20))  # -1.61%

    mock_send.assert_awaited_once()
    assert "bajo 1.61%" in mock_send.call_args.kwargs["text"]
    assert await repository.get_reference(SELL) == Decimal("12.20")


@pytest.mark.asyncio
async def test_buy_and_sell_are_evaluated_independently(repository):
    """Un movimiento fuerte en venta no debe gatillar ni tocar la
    referencia de compra, y viceversa."""

    notifier = PriceAlertNotifier(_settings(threshold=1.0), repository)
    await repository.set_reference(BUY, Decimal("12.00"))
    await repository.set_reference(SELL, Decimal("12.40"))

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        # compra se mueve fuerte (+2%), venta casi nada (+0.08%)
        await notifier.check_and_notify(_items(buy=12.24, sell=12.41))

    mock_send.assert_awaited_once()
    assert "Binance P2P compra" in mock_send.call_args.kwargs["text"]
    assert await repository.get_reference(BUY) == Decimal("12.24")
    assert await repository.get_reference(SELL) == Decimal("12.40")  # sin cambios


@pytest.mark.asyncio
async def test_reference_not_updated_when_telegram_send_fails(repository):
    """Si el envio falla (bot caido, chat_id invalido), no se "rearma" la
    referencia -- la proxima corrida vuelve a intentar con el mismo
    movimiento acumulado en vez de perder el evento en silencio."""

    notifier = PriceAlertNotifier(_settings(threshold=1.0), repository)
    await repository.set_reference(BUY, Decimal("12.00"))

    with patch("telegram.Bot.send_message", new=AsyncMock(side_effect=RuntimeError("caido"))):
        await notifier.check_and_notify(_items(buy=12.50))

    assert await repository.get_reference(BUY) == Decimal("12.00")


@pytest.mark.asyncio
async def test_disabled_without_bot_token_does_nothing(repository):
    notifier = PriceAlertNotifier(_settings(token=None), repository)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(buy=12.20))

    mock_send.assert_not_awaited()
    assert await repository.get_reference(BUY) is None


@pytest.mark.asyncio
async def test_disabled_without_chat_id_does_nothing(repository):
    notifier = PriceAlertNotifier(_settings(chat_id=None), repository)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(buy=12.20))

    mock_send.assert_not_awaited()
    assert await repository.get_reference(BUY) is None


@pytest.mark.asyncio
async def test_ignores_untracked_indicator_codes(repository):
    """El oficial del BCB (u otro indicador no trackeado) no debe hacer
    nada, ni siquiera establecer una referencia."""

    notifier = PriceAlertNotifier(_settings(), repository)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(
            [{"indicator_code": "bcb_tipo_de_cambio_oficial", "value": 12.55}]
        )

    mock_send.assert_not_awaited()
    assert await repository.get_reference("bcb_tipo_de_cambio_oficial") is None


@pytest.mark.asyncio
async def test_start_command_replies_with_welcome(repository):
    """El bot debe responder /start (no quedar mudo como antes) con una
    bienvenida que explique las alertas y los comandos disponibles."""

    notifier = PriceAlertNotifier(_settings(), repository)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.handle_message("123456", "/start")

    mock_send.assert_awaited_once()
    text = mock_send.call_args.kwargs["text"]
    assert "Alertas de precio" in text
    assert "/precio" in text
    assert "1%" in text


@pytest.mark.asyncio
async def test_message_from_unconfigured_chat_is_ignored(repository):
    """El bot es personal: un mensaje desde un chat distinto al configurado
    se ignora por completo (no responde nada)."""

    notifier = PriceAlertNotifier(_settings(), repository)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.handle_message("999999", "/start")

    mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_help_command_replies_with_command_list(repository):
    notifier = PriceAlertNotifier(_settings(), repository)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.handle_message("123456", "/ayuda")

    mock_send.assert_awaited_once()
    assert "/precio" in mock_send.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_price_command_returns_current_prices(session_maker):
    """/precio responde el oficial del BCB y la compra/venta P2P con el
    ultimo valor guardado, en ese orden."""

    from src.db.indicators import EconomicIndicatorRepository

    repo = EconomicIndicatorRepository(session_maker)
    await repo.save_values(
        [
            {
                "source": "bcb",
                "indicator_code": "bcb_tipo_de_cambio_oficial",
                "indicator_name": "Tipo de cambio oficial",
                "indicator_group": "dolar",
                "value": 12.55,
            },
            {
                "source": "binance",
                "indicator_code": "binance_p2p_usdt_bob_buy",
                "indicator_name": "P2P compra",
                "indicator_group": "dolar",
                "value": 12.20,
            },
            {
                "source": "binance",
                "indicator_code": "binance_p2p_usdt_bob_sell",
                "indicator_name": "P2P venta",
                "indicator_group": "dolar",
                "value": 12.40,
            },
        ]
    )

    notifier = PriceAlertNotifier(_settings(), PriceAlertRepository(session_maker), session_maker)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.handle_message("123456", "/precio")

    mock_send.assert_awaited_once()
    text = mock_send.call_args.kwargs["text"]
    assert text.index("Dolar oficial BCB: Bs 12.55") < text.index("Binance P2P compra: Bs 12.20")
    assert "Binance P2P compra: Bs 12.20" in text
    assert "Binance P2P venta: Bs 12.40" in text
    assert "Actualizado:" in text


@pytest.mark.asyncio
async def test_price_command_without_db_replies_unavailable(repository):
    notifier = PriceAlertNotifier(_settings(), repository, session_maker=None)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.handle_message("123456", "/precio")

    mock_send.assert_awaited_once()
    assert "no esta disponible" in mock_send.call_args.kwargs["text"]


class _FakeBot:
    def __init__(self, notifier, updates):
        self.notifier = notifier
        self.updates = list(updates)
        self.calls = []
        self.sent = []

    async def get_updates(self, **kwargs):
        self.calls.append(kwargs)
        if self.updates:
            return [self.updates.pop(0)]
        self.notifier._stopped = True
        return []

    async def send_message(self, **kwargs):
        self.sent.append(kwargs)


@pytest.mark.asyncio
async def test_polling_loop_processes_incoming_message_and_tracks_offset(repository):
    """El long-polling lee updates, responde los comandos y mantiene el
    offset para no volver a procesar los mismos mensajes."""

    notifier = PriceAlertNotifier(_settings(), repository)
    fake = _FakeBot(
        notifier,
        [
            SimpleNamespace(
                update_id=5,
                message=SimpleNamespace(
                    text="/start",
                    chat=SimpleNamespace(id="123456"),
                    from_user=None,
                ),
            )
        ],
    )
    notifier.bot = fake
    notifier._stopped = False

    await notifier._poll_loop()

    assert fake.sent
    assert "Alertas de precio" in fake.sent[0]["text"]
    assert fake.calls[0]["offset"] is None
    assert fake.calls[1]["offset"] == 6
