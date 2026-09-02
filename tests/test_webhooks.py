import hashlib
import hmac
import json
from types import SimpleNamespace

import httpx
import pytest

import src.main as main_module
from src.main import app


def _whatsapp_payload(sender: str, body: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"from": sender, "type": "text", "text": {"body": body}}
                            ]
                        },
                        "field": "messages",
                    }
                ]
            }
        ],
    }


class FakeWhatsApp:
    def __init__(self, reply: str | None = "hola"):
        self.reply = reply
        self.calls: list[tuple[str, str]] = []
        self.events: list[dict] = []

    async def handle_message(self, from_number, body):
        self.calls.append((from_number, body))
        return self.reply

    async def process_webhook_event(self, payload):
        self.events.append(payload)
        extracted = None
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                for message in change.get("value", {}).get("messages", []):
                    extracted = (message.get("from"), (message.get("text") or {}).get("body", ""))
        if extracted:
            await self.handle_message(*extracted)


class FakeTelegram:
    def __init__(self):
        self.payloads: list[dict] = []

    async def process_update(self, payload):
        self.payloads.append(payload)


@pytest.fixture
def fake_app_instance():
    original = main_module.app_instance
    whatsapp = FakeWhatsApp()
    telegram = FakeTelegram()
    main_module.app_instance = SimpleNamespace(
        whatsapp=whatsapp,
        telegram=telegram,
        settings=SimpleNamespace(
            telegram_webhook_secret=None,
            whatsapp_meta_verify_token=None,
            whatsapp_meta_app_secret=None,
        ),
    )
    try:
        yield SimpleNamespace(whatsapp=whatsapp, telegram=telegram)
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_whatsapp_webhook_verify_handshake_returns_challenge():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        whatsapp=FakeWhatsApp(),
        telegram=None,
        settings=SimpleNamespace(whatsapp_meta_verify_token="my-verify-token"),
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/webhook/whatsapp",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "my-verify-token",
                    "hub.challenge": "123456",
                },
            )
    finally:
        main_module.app_instance = original

    assert response.status_code == 200
    assert response.text == "123456"


@pytest.mark.asyncio
async def test_whatsapp_webhook_verify_handshake_rejects_wrong_token():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        whatsapp=FakeWhatsApp(),
        telegram=None,
        settings=SimpleNamespace(whatsapp_meta_verify_token="my-verify-token"),
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/webhook/whatsapp",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "wrong-token",
                    "hub.challenge": "123456",
                },
            )
    finally:
        main_module.app_instance = original

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_whatsapp_webhook_forwards_meta_payload_to_handler(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    payload = _whatsapp_payload("59171234567", "hola")
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/webhook/whatsapp", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake_app_instance.whatsapp.events == [payload]
    assert fake_app_instance.whatsapp.calls == [("59171234567", "hola")]


@pytest.mark.asyncio
async def test_whatsapp_webhook_requires_whatsapp_handler():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(whatsapp=None, telegram=None, settings=SimpleNamespace())
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/webhook/whatsapp", json=_whatsapp_payload("591700000", "hola"))
    finally:
        main_module.app_instance = original

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_whatsapp_webhook_rejects_invalid_meta_signature():
    whatsapp = FakeWhatsApp()
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        whatsapp=whatsapp,
        telegram=None,
        settings=SimpleNamespace(whatsapp_meta_app_secret="fake-app-secret"),
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/webhook/whatsapp",
                json=_whatsapp_payload("591700000", "hola"),
                headers={"X-Hub-Signature-256": "sha256=not-the-real-signature"},
            )
    finally:
        main_module.app_instance = original

    assert response.status_code == 401
    assert whatsapp.events == []


@pytest.mark.asyncio
async def test_whatsapp_webhook_accepts_valid_meta_signature():
    whatsapp = FakeWhatsApp()
    app_secret = "fake-app-secret"
    payload = _whatsapp_payload("591700000", "hola")
    body = json.dumps(payload).encode("utf-8")
    valid_signature = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()

    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        whatsapp=whatsapp,
        telegram=None,
        settings=SimpleNamespace(whatsapp_meta_app_secret=app_secret),
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/webhook/whatsapp",
                content=body,
                headers={"Content-Type": "application/json", "X-Hub-Signature-256": valid_signature},
            )
    finally:
        main_module.app_instance = original

    assert response.status_code == 200
    assert whatsapp.calls == [("591700000", "hola")]


@pytest.mark.asyncio
async def test_whatsapp_webhook_skips_signature_check_when_not_configured(fake_app_instance):
    """Sin WHATSAPP_META_APP_SECRET configurado (dev local, o un despliegue
    que todavia no lo seteo) el webhook sigue funcionando sin validar firma,
    igual que antes de agregar esta proteccion."""

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/webhook/whatsapp", json=_whatsapp_payload("591700000", "hola"))

    assert response.status_code == 200
    assert fake_app_instance.whatsapp.calls == [("591700000", "hola")]


@pytest.mark.asyncio
async def test_telegram_webhook_forwards_payload_to_handler(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    payload = {"update_id": 1, "message": {"text": "/start"}}
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/webhook/telegram", json=payload)

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fake_app_instance.telegram.payloads == [payload]


@pytest.mark.asyncio
async def test_telegram_webhook_requires_telegram_handler():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(whatsapp=None, telegram=None, settings=SimpleNamespace())
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/webhook/telegram", json={"update_id": 1})
    finally:
        main_module.app_instance = original

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_telegram_webhook_rejects_missing_secret_token():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        whatsapp=None,
        telegram=FakeTelegram(),
        settings=SimpleNamespace(telegram_webhook_secret="super-secret"),
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/webhook/telegram", json={"update_id": 1})
    finally:
        main_module.app_instance = original

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_telegram_webhook_accepts_matching_secret_token():
    telegram = FakeTelegram()
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        whatsapp=None,
        telegram=telegram,
        settings=SimpleNamespace(telegram_webhook_secret="super-secret"),
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/webhook/telegram",
                json={"update_id": 1},
                headers={"X-Telegram-Bot-Api-Secret-Token": "super-secret"},
            )
    finally:
        main_module.app_instance = original

    assert response.status_code == 200
    assert telegram.payloads == [{"update_id": 1}]
