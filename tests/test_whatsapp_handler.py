from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import sentry_sdk

from src.distributors.whatsapp_handler import WhatsAppHandler


def _settings(**overrides):
    base = {
        "twilio_account_sid": None,
        "twilio_auth_token": None,
        "twilio_phone_number": "+14155238886",
        "schedule_summary_morning": "08:00",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class FakeDb:
    def __init__(self):
        self.saved: list[dict] = []
        self.unsubscribed: list[str] = []

    async def save_subscription(self, *, phone, channel, categories, consent_accepted):
        self.saved.append(
            {"phone": phone, "channel": channel, "categories": categories, "consent_accepted": consent_accepted}
        )

    async def unsubscribe(self, phone):
        self.unsubscribed.append(phone)


@pytest.mark.asyncio
async def test_handle_message_without_body_returns_help():
    handler = WhatsAppHandler(settings=_settings())
    result = await handler.handle_message("+591700000", "")
    assert "Ayuda EcoBrief" in result


@pytest.mark.asyncio
async def test_handle_message_greeting_returns_category_menu():
    handler = WhatsAppHandler(settings=_settings())
    result = await handler.handle_message("+591700000", "Hola")
    assert "Selecciona las categorias" in result


@pytest.mark.asyncio
async def test_handle_selection_saves_subscription_and_awaits_db_write():
    db = FakeDb()
    handler = WhatsAppHandler(db_repository=db, settings=_settings())

    result = await handler.handle_message("+591700000", "1 3")

    assert "Preferencias guardadas" in result
    # La escritura debe estar completa ANTES de que handle_message retorne
    # (ya no es un asyncio.create_task en segundo plano que podia perderse).
    assert db.saved == [
        {
            "phone": "+591700000",
            "channel": "whatsapp",
            "categories": {"economia", "deportes"},
            "consent_accepted": True,
        }
    ]


@pytest.mark.asyncio
async def test_handle_selection_with_invalid_input_does_not_touch_db():
    db = FakeDb()
    handler = WhatsAppHandler(db_repository=db, settings=_settings())

    result = await handler.handle_message("+591700000", "no entiendo")

    assert "Seleccion invalida" in result
    assert db.saved == []


@pytest.mark.asyncio
async def test_handle_cancel_unsubscribes_and_awaits_db_write():
    db = FakeDb()
    handler = WhatsAppHandler(db_repository=db, settings=_settings())

    result = await handler.handle_message("+591700000", "cancelar")

    assert "dado de baja" in result
    assert db.unsubscribed == ["+591700000"]


@pytest.mark.asyncio
async def test_handle_message_works_without_db_configured():
    handler = WhatsAppHandler(settings=_settings())
    result = await handler.handle_message("+591700000", "cancelar")
    assert "dado de baja" in result


def test_send_message_without_twilio_client_returns_false():
    handler = WhatsAppHandler(settings=_settings())
    assert handler.send_message("+591700000", "hola") is False


def test_send_message_uses_twilio_client_when_configured():
    handler = WhatsAppHandler(settings=_settings())
    handler.client = MagicMock()

    result = handler.send_message("+591700000", "hola mundo")

    assert result is True
    handler.client.messages.create.assert_called_once_with(
        from_="+14155238886", body="hola mundo", to="whatsapp:+591700000"
    )


def test_send_message_returns_false_when_twilio_raises():
    handler = WhatsAppHandler(settings=_settings())
    handler.client = MagicMock()
    handler.client.messages.create.side_effect = RuntimeError("twilio down")

    assert handler.send_message("+591700000", "hola") is False


def test_send_message_reports_twilio_failures_to_sentry():
    handler = WhatsAppHandler(settings=_settings())
    handler.client = MagicMock()
    boom = RuntimeError("twilio down")
    handler.client.messages.create.side_effect = boom

    with patch.object(sentry_sdk, "capture_exception") as mock_capture:
        result = handler.send_message("+591700000", "hola")

    assert result is False
    mock_capture.assert_called_once_with(boom)
