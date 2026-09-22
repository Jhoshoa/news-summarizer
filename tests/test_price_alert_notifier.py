"""Tests for PriceAlertNotifier: avisa por Telegram cuando compra/venta P2P
se mueve mas de un umbral desde la ULTIMA ALERTA (no desde la corrida
anterior, sin reset por dia) -- ver src/notifiers/price_alert_notifier.py
para el razonamiento completo detras de este diseno.

El bot es de suscripcion abierta (no un bot personal con chat fijo): /start
registra al chat en price_alert_subscribers, /baja lo quita y las alertas
van a todos los suscriptos.
"""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from telegram.error import InvalidToken, TimedOut

from src.db.price_alert_subscribers import PriceAlertSubscriberRepository
from src.db.price_alerts import PriceAlertRepository
from src.db.repository import Base
from src.notifiers.price_alert_notifier import PriceAlertNotifier

BUY = "binance_p2p_usdt_bob_buy"
SELL = "binance_p2p_usdt_bob_sell"


def _settings(token: str | None = "123456:fake-token", threshold: float = 1.0):
    return SimpleNamespace(
        price_alert_bot_token=token,
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


async def _subscribe(session_maker, *chat_ids: str) -> PriceAlertSubscriberRepository:
    repo = PriceAlertSubscriberRepository(session_maker)
    for chat_id in chat_ids:
        await repo.add(chat_id)
    return repo


def _notifier(repository, session_maker, token: str | None = "123456:fake-token"):
    return PriceAlertNotifier(_settings(token=token), repository, session_maker)


def _items(buy=None, sell=None, collected_at=None) -> list[dict]:
    items = []
    if buy is not None:
        items.append({"indicator_code": BUY, "value": buy, "collected_at": collected_at})
    if sell is not None:
        items.append({"indicator_code": SELL, "value": sell, "collected_at": collected_at})
    return items


@pytest.mark.asyncio
async def test_first_observation_sets_baseline_without_alerting(session_maker, repository):
    await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(buy=12.20))

    mock_send.assert_not_awaited()
    assert await repository.get_reference(BUY) == Decimal("12.20")


@pytest.mark.asyncio
async def test_no_alerts_without_subscribers_does_nothing(session_maker, repository):
    """Sin suscriptores no se gestiona ni siquiera la referencia: no hay a
    quien avisar, asi que no tiene sentido guardar un punto de partida."""

    notifier = _notifier(repository, session_maker)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(buy=12.20))

    mock_send.assert_not_awaited()
    assert await repository.get_reference(BUY) is None


@pytest.mark.asyncio
async def test_alerts_when_move_meets_or_exceeds_threshold(session_maker, repository):
    await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker)
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
async def test_alert_message_includes_reference_time_value_and_calculation(session_maker, repository):
    """El aviso explica contra que se calculo: el valor referencial (y su
    hora real), el precio actual (y su hora), la variacion en % y en Bs, y
    el criterio (comparacion contra la ultima alerta)."""

    await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker)
    await repository.set_reference(
        BUY,
        Decimal("12.00"),
        collected_at=datetime(2026, 9, 22, 11, 32),
    )

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(
            _items(buy=12.12, collected_at=datetime(2026, 9, 22, 11, 35))
        )

    mock_send.assert_awaited_once()
    text = mock_send.call_args.kwargs["text"]
    assert "subio 1.00% (+Bs 0.12)" in text
    assert "Referencia (ultima alerta): Bs 12.00 - 22/09/2026 11:32" in text
    assert "Precio actual: Bs 12.12 - 22/09/2026 11:35" in text
    assert "Se compara contra la ultima alerta enviada" in text
    # El nuevo valor (con su hora) queda como referencia del proximo aviso.
    ref, ref_time = await repository.get_reference_with_time(BUY)
    assert ref == Decimal("12.12")
    assert ref_time == datetime(2026, 9, 22, 11, 35)


@pytest.mark.asyncio
async def test_does_not_alert_when_move_is_under_threshold(session_maker, repository):
    await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker)
    await repository.set_reference(BUY, Decimal("12.00"))

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(buy=12.05))  # +0.42%

    mock_send.assert_not_awaited()
    # La referencia NO se mueve si no hubo alerta -- el proximo chequeo debe
    # seguir comparando contra el mismo punto de partida (12.00), no contra
    # este ultimo valor visto (12.05).
    assert await repository.get_reference(BUY) == Decimal("12.00")


@pytest.mark.asyncio
async def test_downward_move_also_triggers_alert_with_correct_wording(session_maker, repository):
    await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker)
    await repository.set_reference(SELL, Decimal("12.40"))

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(sell=12.20))  # -1.61%

    mock_send.assert_awaited_once()
    assert "bajo 1.61%" in mock_send.call_args.kwargs["text"]
    assert await repository.get_reference(SELL) == Decimal("12.20")


@pytest.mark.asyncio
async def test_buy_and_sell_are_evaluated_independently(session_maker, repository):
    """Un movimiento fuerte en venta no debe gatillar ni tocar la
    referencia de compra, y viceversa."""

    await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker)
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
async def test_alert_sent_to_all_subscribers(session_maker, repository):
    await _subscribe(session_maker, "111", "222")
    notifier = _notifier(repository, session_maker)
    await repository.set_reference(BUY, Decimal("12.00"))

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(buy=12.20))  # +1.67%

    assert mock_send.await_count == 2
    sent_chats = {call.kwargs["chat_id"] for call in mock_send.await_args_list}
    assert sent_chats == {"111", "222"}
    assert await repository.get_reference(BUY) == Decimal("12.20")


@pytest.mark.asyncio
async def test_reference_not_updated_when_telegram_send_fails(session_maker, repository):
    """Si el envio falla (bot caido, chat invalido), no se "rearma" la
    referencia -- la proxima corrida vuelve a intentar con el mismo
    movimiento acumulado en vez de perder el evento en silencio."""

    await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker)
    await repository.set_reference(BUY, Decimal("12.00"))

    with patch("telegram.Bot.send_message", new=AsyncMock(side_effect=RuntimeError("caido"))):
        await notifier.check_and_notify(_items(buy=12.50))

    assert await repository.get_reference(BUY) == Decimal("12.00")


@pytest.mark.asyncio
async def test_reference_not_rearmed_when_one_subscriber_fails(session_maker, repository):
    """Si un solo suscriptor falla, no se rearma: el que no recibio el aviso
    no debe perder el evento para siempre (los demas podran ver un duplicado
    en el proximo intento, menos grave)."""

    await _subscribe(session_maker, "111", "BAD")
    notifier = _notifier(repository, session_maker)
    await repository.set_reference(BUY, Decimal("12.00"))

    async def _fail_for_bad(**kwargs):
        if kwargs["chat_id"] == "BAD":
            raise RuntimeError("caido")

    with patch("telegram.Bot.send_message", new=AsyncMock(side_effect=_fail_for_bad)) as mock_send:
        await notifier.check_and_notify(_items(buy=12.20))

    assert mock_send.await_count == 2
    assert await repository.get_reference(BUY) == Decimal("12.00")


@pytest.mark.asyncio
async def test_disabled_without_bot_token_does_nothing(session_maker, repository):
    await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker, token=None)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(buy=12.20))

    mock_send.assert_not_awaited()
    assert await repository.get_reference(BUY) is None


@pytest.mark.asyncio
async def test_disabled_without_session_maker_does_nothing(repository, session_maker):
    """Sin DB no se puede leer la lista de suscriptores ni la referencia, asi
    que el chequeo de alertas queda deshabilitado."""

    notifier = PriceAlertNotifier(_settings(), repository, session_maker=None)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(_items(buy=12.20))

    mock_send.assert_not_awaited()
    assert await repository.get_reference(BUY) is None


@pytest.mark.asyncio
async def test_ignores_untracked_indicator_codes(session_maker, repository):
    """El oficial del BCB (u otro indicador no trackeado) no debe hacer
    nada, ni siquiera establecer una referencia."""

    await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.check_and_notify(
            [{"indicator_code": "bcb_tipo_de_cambio_oficial", "value": 12.55}]
        )

    mock_send.assert_not_awaited()
    assert await repository.get_reference("bcb_tipo_de_cambio_oficial") is None


@pytest.mark.asyncio
async def test_start_command_registers_subscriber_and_replies_welcome(session_maker, repository):
    """/start responde la bienvenida Y registra al chat en
    price_alert_subscribers (el bot es de suscripcion abierta, no queda mudo
    ni limitado a un chat fijo como antes)."""

    notifier = _notifier(repository, session_maker)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.handle_message("123456", "/start")

    mock_send.assert_awaited_once()
    text = mock_send.call_args.kwargs["text"]
    assert "Alertas de precio" in text
    assert "Estas suscripto" in text
    assert "/precio" in text
    assert "/baja" in text
    assert "1%" in text

    sub_repo = PriceAlertSubscriberRepository(session_maker)
    assert await sub_repo.is_subscribed("123456")


@pytest.mark.asyncio
async def test_start_is_idempotent(session_maker, repository):
    sub_repo = await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker)

    with patch("telegram.Bot.send_message", new=AsyncMock()):
        await notifier.handle_message("123456", "/start")

    assert await sub_repo.list_chat_ids() == ["123456"]


@pytest.mark.asyncio
async def test_anyone_can_ask_for_current_prices(session_maker, repository):
    """Al no haber chat fijo, /precio responde aunque el chat no este
    registrado (consultar precios no requiere suscribirse)."""

    from src.db.indicators import EconomicIndicatorRepository

    await EconomicIndicatorRepository(session_maker).save_values(
        [
            {
                "source": "bcb",
                "indicator_code": "bcb_tipo_de_cambio_oficial",
                "indicator_name": "Tipo de cambio oficial",
                "indicator_group": "dolar",
                "value": 12.55,
            },
        ]
    )
    notifier = _notifier(repository, session_maker)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.handle_message("999999", "/precio")

    mock_send.assert_awaited_once()
    assert "Dolar oficial BCB: Bs 12.55" in mock_send.call_args.kwargs["text"]
    assert not await PriceAlertSubscriberRepository(session_maker).is_subscribed("999999")


@pytest.mark.asyncio
async def test_baja_removes_subscriber_and_confirms(session_maker, repository):
    sub_repo = await _subscribe(session_maker, "123456")
    notifier = _notifier(repository, session_maker)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.handle_message("123456", "/baja")

    mock_send.assert_awaited_once()
    assert "Ya no recibiras alertas" in mock_send.call_args.kwargs["text"]
    assert not await sub_repo.is_subscribed("123456")


@pytest.mark.asyncio
async def test_help_command_replies_with_command_list(repository, session_maker):
    notifier = _notifier(repository, session_maker)

    with patch("telegram.Bot.send_message", new=AsyncMock()) as mock_send:
        await notifier.handle_message("123456", "/ayuda")

    mock_send.assert_awaited_once()
    assert "/precio" in mock_send.call_args.kwargs["text"]
    assert "/start" in mock_send.call_args.kwargs["text"]
    assert "/baja" in mock_send.call_args.kwargs["text"]


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
async def test_polling_loop_processes_incoming_message_and_tracks_offset(session_maker, repository):
    """El long-polling lee updates, responde los comandos y mantiene el
    offset para no volver a procesar los mismos mensajes."""

    notifier = _notifier(repository, session_maker)
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


class _AlwaysRaiseBot:
    def __init__(self, notifier, exc):
        self.notifier = notifier
        self.exc = exc
        self.calls = 0

    async def get_updates(self, **kwargs):
        self.calls += 1
        raise self.exc


class _OneErrorThenEmptyBot:
    def __init__(self, notifier, exc):
        self.notifier = notifier
        self.exc = exc
        self.calls = []

    async def get_updates(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            raise self.exc
        self.notifier._stopped = True
        return []


@pytest.mark.asyncio
async def test_invalid_token_format_disables_notifier(session_maker, repository):
    """Un PRICE_ALERT_BOT_TOKEN sin el prefijo <bot_id>: no puede existir en
    Telegram: se deshabilita el notifier sin siquiera tocar la red."""

    notifier = PriceAlertNotifier(_settings(token="token-sin-colon"), repository, session_maker)

    assert notifier.bot is None
    assert not notifier.enabled


@pytest.mark.asyncio
async def test_start_polling_disables_notifier_when_token_not_valid(session_maker, repository):
    """Si get_me falla el token no pertenece a un bot valido: start_polling
    NO arranca el loop (falla rapido en vez de reintentar para siempre)."""

    notifier = _notifier(repository, session_maker)
    assert notifier.bot is not None

    with patch(
        "telegram.Bot.get_me",
        new=AsyncMock(side_effect=InvalidToken("Not Found")),
    ):
        await notifier.start_polling()

    assert notifier.bot is None
    assert notifier._poll_task is None


@pytest.mark.asyncio
async def test_poll_loop_stops_on_fatal_invalid_token(session_maker, repository):
    """Un token invalido/revocado es fatal: el loop se detiene despues del
    primer error (no reintenta, no duerme) y deshabilita el notifier."""

    notifier = _notifier(repository, session_maker)
    fake = _AlwaysRaiseBot(notifier, InvalidToken("Not Found"))
    notifier.bot = fake
    notifier._stopped = False

    await notifier._poll_loop()

    assert fake.calls == 1
    assert notifier.bot is None


@pytest.mark.asyncio
async def test_poll_loop_retries_on_transient_error(session_maker, repository):
    """Los errores transitorios (timeout, red) no detienen el loop: se
    reintenta con backoff y sigue escuchando."""

    notifier = _notifier(repository, session_maker)
    fake = _OneErrorThenEmptyBot(notifier, TimedOut("timeout"))
    notifier.bot = fake
    notifier._stopped = False

    with patch(
        "src.notifiers.price_alert_notifier.asyncio.sleep",
        new=AsyncMock(),
    ) as mock_sleep:
        await notifier._poll_loop()

    assert len(fake.calls) == 2
    assert mock_sleep.await_count == 1
    assert notifier.bot is not None
