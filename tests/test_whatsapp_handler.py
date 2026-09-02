from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
import sentry_sdk

from src.distributors.whatsapp_handler import WhatsAppHandler


def _settings(**overrides):
    base = {
        "whatsapp_meta_access_token": None,
        "whatsapp_meta_phone_number_id": None,
        "whatsapp_meta_api_version": "v21.0",
        "whatsapp_meta_verify_token": None,
        "whatsapp_meta_app_secret": None,
        "schedule_summary_morning": "08:00",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _configured_settings(**overrides):
    return _settings(
        whatsapp_meta_access_token="fake-permanent-token",
        whatsapp_meta_phone_number_id="1234567890",
        **overrides,
    )


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


def test_is_configured_false_without_credentials():
    handler = WhatsAppHandler(settings=_settings())
    assert handler.is_configured is False


def test_is_configured_true_with_credentials():
    handler = WhatsAppHandler(settings=_configured_settings())
    assert handler.is_configured is True


@pytest.mark.asyncio
async def test_send_message_without_meta_credentials_returns_false():
    handler = WhatsAppHandler(settings=_settings())
    assert await handler.send_message("+591700000", "hola") is False


@pytest.mark.asyncio
async def test_send_message_calls_meta_graph_api():
    handler = WhatsAppHandler(settings=_configured_settings())
    requests_seen = []

    def responder(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.123"}]})

    handler._client = httpx.AsyncClient(
        base_url="https://graph.facebook.com/v21.0",
        headers={"Authorization": "Bearer fake-permanent-token"},
        transport=httpx.MockTransport(responder),
    )

    result = await handler.send_message("+591 700-00000", "hola mundo")

    assert result is True
    assert len(requests_seen) == 1
    request = requests_seen[0]
    assert request.url.path == "/v21.0/1234567890/messages"
    assert request.headers["authorization"] == "Bearer fake-permanent-token"
    import json

    body = json.loads(request.content)
    assert body == {
        "messaging_product": "whatsapp",
        "to": "59170000000",
        "type": "text",
        "text": {"body": "hola mundo"},
    }

    await handler.close()


@pytest.mark.asyncio
async def test_send_message_returns_false_when_meta_api_errors():
    handler = WhatsAppHandler(settings=_configured_settings())

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "Invalid parameter"}})

    handler._client = httpx.AsyncClient(
        base_url="https://graph.facebook.com/v21.0",
        transport=httpx.MockTransport(responder),
    )

    assert await handler.send_message("+591700000", "hola") is False
    await handler.close()


@pytest.mark.asyncio
async def test_send_message_reports_meta_api_failures_to_sentry():
    handler = WhatsAppHandler(settings=_configured_settings())

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "Internal error"}})

    handler._client = httpx.AsyncClient(
        base_url="https://graph.facebook.com/v21.0",
        transport=httpx.MockTransport(responder),
    )

    with patch.object(sentry_sdk, "capture_exception") as mock_capture:
        result = await handler.send_message("+591700000", "hola")

    assert result is False
    mock_capture.assert_called_once()
    await handler.close()


def test_verify_webhook_signature_accepts_when_app_secret_not_configured():
    assert WhatsAppHandler.verify_webhook_signature(None, b"{}", None) is True


def test_verify_webhook_signature_rejects_missing_header_when_configured():
    assert WhatsAppHandler.verify_webhook_signature("secret", b"{}", None) is False


def test_verify_webhook_signature_rejects_wrong_signature():
    assert (
        WhatsAppHandler.verify_webhook_signature("secret", b'{"a":1}', "sha256=not-the-real-one")
        is False
    )


def test_verify_webhook_signature_accepts_correct_signature():
    import hashlib
    import hmac

    body = b'{"a":1}'
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    assert WhatsAppHandler.verify_webhook_signature("secret", body, signature) is True


def test_extract_inbound_message_reads_meta_nested_payload():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-id",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "1234567890"},
                            "messages": [
                                {
                                    "from": "59171234567",
                                    "id": "wamid.abc",
                                    "type": "text",
                                    "text": {"body": "hola"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    assert WhatsAppHandler.extract_inbound_message(payload) == ("59171234567", "hola")


def test_extract_inbound_message_ignores_non_text_events():
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [{"id": "wamid.abc", "status": "delivered"}],
                        }
                    }
                ]
            }
        ]
    }

    assert WhatsAppHandler.extract_inbound_message(payload) is None


def test_extract_inbound_message_handles_malformed_payload():
    assert WhatsAppHandler.extract_inbound_message({}) is None
    assert WhatsAppHandler.extract_inbound_message({"entry": "not-a-list"}) is None


@pytest.mark.asyncio
async def test_process_webhook_event_replies_via_send_message():
    handler = WhatsAppHandler(settings=_configured_settings())
    sent: list[tuple[str, str]] = []

    async def fake_send_message(to, message):
        sent.append((to, message))
        return True

    handler.send_message = fake_send_message

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"from": "59171234567", "type": "text", "text": {"body": "hola"}}
                            ]
                        }
                    }
                ]
            }
        ]
    }

    await handler.process_webhook_event(payload)

    assert len(sent) == 1
    assert sent[0][0] == "59171234567"
    assert "Selecciona las categorias" in sent[0][1]


@pytest.mark.asyncio
async def test_process_webhook_event_does_nothing_for_non_message_events():
    handler = WhatsAppHandler(settings=_configured_settings())
    sent: list[tuple[str, str]] = []

    async def fake_send_message(to, message):
        sent.append((to, message))
        return True

    handler.send_message = fake_send_message

    await handler.process_webhook_event({"entry": [{"changes": [{"value": {"statuses": []}}]}]})

    assert sent == []


@pytest.mark.asyncio
async def test_process_webhook_event_swallows_errors():
    handler = WhatsAppHandler(settings=_configured_settings())

    async def failing_send_message(to, message):
        raise RuntimeError("meta down")

    handler.send_message = failing_send_message

    payload = {
        "entry": [
            {
                "changes": [
                    {"value": {"messages": [{"from": "591700000", "type": "text", "text": {"body": "hola"}}]}}
                ]
            }
        ]
    }

    with patch.object(sentry_sdk, "capture_exception") as mock_capture:
        await handler.process_webhook_event(payload)

    mock_capture.assert_called_once()
