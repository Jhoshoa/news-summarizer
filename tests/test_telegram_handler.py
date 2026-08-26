from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import sentry_sdk

from src.distributors.telegram_handler import TelegramHandler


def _settings(token: str | None = "fake-token"):
    return SimpleNamespace(telegram_bot_token=token)


class FakeDb:
    def __init__(self):
        self.saved: list[dict] = []
        self.unsubscribed: list[str] = []

    async def save_subscription(self, *, telegram_id, channel, categories, consent_accepted):
        self.saved.append(
            {
                "telegram_id": telegram_id,
                "channel": channel,
                "categories": categories,
                "consent_accepted": consent_accepted,
            }
        )

    async def unsubscribe(self, telegram_id):
        self.unsubscribed.append(telegram_id)


def test_handler_without_token_has_no_bot():
    handler = TelegramHandler(settings=_settings(token=None))
    assert handler.bot is None


def test_handler_with_token_creates_bot():
    handler = TelegramHandler(settings=_settings())
    assert handler.bot is not None


@pytest.mark.asyncio
async def test_send_message_without_bot_returns_false_and_does_not_raise():
    handler = TelegramHandler(settings=_settings(token=None))
    result = await handler.send_message("123", "hola")
    assert result is False


@pytest.mark.asyncio
async def test_send_message_uses_bot_send_message():
    handler = TelegramHandler(settings=_settings())

    # Bot es un TelegramObject "congelado" (no se puede setattr una instancia),
    # asi que parcheamos el metodo a nivel de clase en vez de la instancia.
    with patch("telegram.Bot.send_message", new=AsyncMock(return_value=None)) as mock_send:
        result = await handler.send_message("123", "hola mundo")

    assert result is True
    mock_send.assert_awaited_once_with(chat_id="123", text="hola mundo", parse_mode="Markdown")


@pytest.mark.asyncio
async def test_send_message_returns_false_when_telegram_api_fails():
    handler = TelegramHandler(settings=_settings())

    with patch("telegram.Bot.send_message", new=AsyncMock(side_effect=RuntimeError("network down"))):
        result = await handler.send_message("123", "hola")

    assert result is False


@pytest.mark.asyncio
async def test_send_message_reports_telegram_failures_to_sentry():
    handler = TelegramHandler(settings=_settings())
    boom = RuntimeError("network down")

    with (
        patch("telegram.Bot.send_message", new=AsyncMock(side_effect=boom)),
        patch.object(sentry_sdk, "capture_exception") as mock_capture,
    ):
        result = await handler.send_message("123", "hola")

    assert result is False
    mock_capture.assert_called_once_with(boom)


@pytest.mark.asyncio
async def test_process_update_without_bot_is_a_noop():
    handler = TelegramHandler(settings=_settings(token=None))
    await handler.process_update({"update_id": 1})  # no debe lanzar


@pytest.mark.asyncio
async def test_process_update_dispatches_start_command_to_handle_message():
    db = FakeDb()
    handler = TelegramHandler(db_repository=db, settings=_settings())

    payload = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 0,
            "chat": {"id": 555, "type": "private"},
            "text": "/start",
        },
    }

    # handle_message llama update.message.reply_text, que internamente usa el
    # bot adjunto por Update.de_json — parcheamos a nivel de clase para no
    # pegarle a la API real de Telegram (la instancia esta "congelada").
    with patch("telegram.Bot.send_message", new=AsyncMock(return_value=None)):
        await handler.process_update(payload)


@pytest.mark.asyncio
async def test_process_update_malformed_payload_does_not_raise():
    handler = TelegramHandler(settings=_settings())
    await handler.process_update({"not": "a valid telegram update"})


@pytest.mark.asyncio
async def test_process_update_reports_failures_to_sentry():
    handler = TelegramHandler(settings=_settings())
    boom = RuntimeError("malformed update")

    with (
        patch("telegram.Update.de_json", side_effect=boom),
        patch.object(sentry_sdk, "capture_exception") as mock_capture,
    ):
        await handler.process_update({"update_id": 1})

    mock_capture.assert_called_once_with(boom)


@pytest.mark.asyncio
async def test_handle_selection_saves_subscription_with_categories():
    db = FakeDb()
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        message=SimpleNamespace(
            text="1 3",
            chat=SimpleNamespace(id=777),
            reply_text=AsyncMock(),
        )
    )

    result = await handler._handle_selection(update, None, "777", "1 3")

    assert result == "Suscripcion guardada"
    assert db.saved == [
        {
            "telegram_id": "777",
            "channel": "telegram",
            "categories": {"economia", "deportes"},
            "consent_accepted": True,
        }
    ]


@pytest.mark.asyncio
async def test_handle_cancel_unsubscribes_via_db():
    db = FakeDb()
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=888), reply_text=AsyncMock())
    )

    result = await handler._handle_cancel(update, None)

    assert result == "Dado de baja"
    assert db.unsubscribed == ["888"]
