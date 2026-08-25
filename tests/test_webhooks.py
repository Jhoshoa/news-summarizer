from types import SimpleNamespace

import httpx
import pytest
from twilio.request_validator import RequestValidator

import src.main as main_module
from src.main import app


class FakeWhatsApp:
    def __init__(self, reply: str | None = "hola"):
        self.reply = reply
        self.calls: list[tuple[str, str]] = []

    async def handle_message(self, from_number, body):
        self.calls.append((from_number, body))
        return self.reply


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
        settings=SimpleNamespace(telegram_webhook_secret=None),
    )
    try:
        yield SimpleNamespace(whatsapp=whatsapp, telegram=telegram)
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_whatsapp_webhook_strips_prefix_and_returns_twiml(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/webhook/whatsapp",
            data={"From": "whatsapp:+59171234567", "Body": "hola"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Message>hola</Message>" in response.text
    assert fake_app_instance.whatsapp.calls == [("+59171234567", "hola")]


@pytest.mark.asyncio
async def test_whatsapp_webhook_escapes_reply_text(fake_app_instance):
    fake_app_instance.whatsapp.reply = "1 < 2 & 3 > 0"
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/webhook/whatsapp", data={"From": "whatsapp:+591700000", "Body": "hola"}
        )

    assert "1 &lt; 2 &amp; 3 &gt; 0" in response.text


@pytest.mark.asyncio
async def test_whatsapp_webhook_returns_empty_response_when_no_reply(fake_app_instance):
    fake_app_instance.whatsapp.reply = None
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/webhook/whatsapp", data={"From": "whatsapp:+591700000", "Body": ""}
        )

    assert response.status_code == 200
    assert "<Response></Response>" in response.text


@pytest.mark.asyncio
async def test_whatsapp_webhook_requires_whatsapp_handler():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(whatsapp=None, telegram=None, settings=SimpleNamespace())
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/webhook/whatsapp", data={"From": "whatsapp:+591700000", "Body": "hola"}
            )
    finally:
        main_module.app_instance = original

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_whatsapp_webhook_rejects_invalid_twilio_signature():
    whatsapp = FakeWhatsApp()
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        whatsapp=whatsapp,
        telegram=None,
        settings=SimpleNamespace(
            twilio_auth_token="fake-auth-token",
            twilio_webhook_url="https://ecobriefbolivia.online/webhook/whatsapp",
        ),
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/webhook/whatsapp",
                data={"From": "whatsapp:+591700000", "Body": "hola"},
                headers={"X-Twilio-Signature": "not-the-real-signature"},
            )
    finally:
        main_module.app_instance = original

    assert response.status_code == 401
    assert whatsapp.calls == []


@pytest.mark.asyncio
async def test_whatsapp_webhook_accepts_valid_twilio_signature():
    whatsapp = FakeWhatsApp()
    webhook_url = "https://ecobriefbolivia.online/webhook/whatsapp"
    auth_token = "fake-auth-token"
    params = {"From": "whatsapp:+591700000", "Body": "hola"}
    valid_signature = RequestValidator(auth_token).compute_signature(webhook_url, params)

    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        whatsapp=whatsapp,
        telegram=None,
        settings=SimpleNamespace(twilio_auth_token=auth_token, twilio_webhook_url=webhook_url),
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/webhook/whatsapp",
                data=params,
                headers={"X-Twilio-Signature": valid_signature},
            )
    finally:
        main_module.app_instance = original

    assert response.status_code == 200
    assert whatsapp.calls == [("+591700000", "hola")]


@pytest.mark.asyncio
async def test_whatsapp_webhook_skips_signature_check_when_not_configured(fake_app_instance):
    """Sin TWILIO_AUTH_TOKEN/TWILIO_WEBHOOK_URL configurados (dev local, o un
    despliegue que todavia no lo seteo) el webhook sigue funcionando sin
    validar firma, igual que antes de agregar esta proteccion."""

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/webhook/whatsapp",
            data={"From": "whatsapp:+591700000", "Body": "hola"},
        )

    assert response.status_code == 200
    assert fake_app_instance.whatsapp.calls == [("+591700000", "hola")]


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
