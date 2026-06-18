from types import SimpleNamespace

import httpx
import pytest

import src.main as main_module
from src.main import app


class FakePreferencesDatabase:
    def __init__(self):
        self.saved = []
        self.unsubscribed = []
        self.preview_categories = []

    async def save_subscription(self, **kwargs):
        self.saved.append(kwargs)
        return True

    async def unsubscribe(self, identifier):
        self.unsubscribed.append(identifier)
        return True

    async def get_preference_preview(self, categories):
        self.preview_categories.append(categories)
        return [
            {
                "category": categories[0],
                "title": "Brief de prueba",
                "summary": "Resumen reciente para preview.",
                "fact": None,
                "summary_date": "2026-06-06",
            }
        ]


@pytest.fixture
def fake_app_instance():
    original = main_module.app_instance
    db = FakePreferencesDatabase()
    main_module.app_instance = SimpleNamespace(
        db=db,
        settings=SimpleNamespace(
            summary_candidates_per_category=8,
            summary_candidates_extended_limit=8,
            summary_candidates_extended_categories="politica, economia",
            telegram_bot_token=None,
            twilio_account_sid=None,
            email_enabled=False,
        ),
    )
    try:
        yield db
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_preference_options_returns_categories_channels_and_frequencies(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/preferences/options")

    assert response.status_code == 200
    payload = response.json()
    assert {"slug": "economia", "label": "Economia", "enabled": True, "note": None} in payload[
        "categories"
    ]
    assert payload["channels"][0]["slug"] == "email"
    assert payload["channels"][0]["enabled"] is True
    assert payload["channels"][1]["slug"] == "whatsapp"
    assert payload["channels"][1]["enabled"] is True
    assert payload["channels"][2]["slug"] == "telegram"
    assert payload["channels"][2]["enabled"] is False
    assert {item["slug"] for item in payload["frequencies"]} == {
        "diario",
        "dias_habiles",
        "tres_veces_semana",
        "semanal",
    }
    assert {item["slug"] for item in payload["preferred_times"]} == {"manana", "tarde", "noche"}


@pytest.mark.asyncio
async def test_subscribe_saves_normalized_whatsapp_preferences(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/subscribe",
            json={
                "channel": "whatsapp",
                "phone": "591 700-00000",
                "categories": ["politica", "economia"],
                "frequency": "diario",
                "preferred_time": "manana",
                "timezone": "America/La_Paz",
                "consent_accepted": True,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "saved"
    assert payload["categories"] == ["economia", "politica"]
    assert fake_app_instance.saved == [
        {
            "phone": "+59170000000",
            "telegram_id": None,
            "email": None,
            "channel": "whatsapp",
            "categories": {"economia", "politica"},
            "frequency": "diario",
            "preferred_time": "manana",
            "timezone": "America/La_Paz",
            "consent_accepted": True,
        }
    ]


@pytest.mark.asyncio
async def test_subscribe_rejects_missing_consent(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/subscribe",
            json={
                "channel": "whatsapp",
                "phone": "+59170000000",
                "categories": ["economia"],
                "consent_accepted": False,
            },
        )

    assert response.status_code == 422
    assert fake_app_instance.saved == []


@pytest.mark.asyncio
async def test_subscribe_saves_normalized_email_preferences(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/subscribe",
            json={
                "channel": "email",
                "email": " Persona@Example.COM ",
                "categories": ["general"],
                "frequency": "semanal",
                "preferred_time": "noche",
                "timezone": "America/La_Paz",
                "consent_accepted": True,
            },
        )

    assert response.status_code == 200
    assert fake_app_instance.saved == [
        {
            "phone": None,
            "telegram_id": None,
            "email": "persona@example.com",
            "channel": "email",
            "categories": {"general"},
            "frequency": "semanal",
            "preferred_time": "noche",
            "timezone": "America/La_Paz",
            "consent_accepted": True,
        }
    ]


@pytest.mark.asyncio
async def test_subscribe_rejects_invalid_email(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/subscribe",
            json={
                "channel": "email",
                "email": "bad",
                "categories": ["general"],
                "consent_accepted": True,
            },
        )

    assert response.status_code == 422
    assert fake_app_instance.saved == []


@pytest.mark.asyncio
async def test_subscribe_rejects_invalid_category(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/subscribe",
            json={
                "channel": "whatsapp",
                "phone": "+59170000000",
                "categories": ["invalida"],
                "consent_accepted": True,
            },
        )

    assert response.status_code == 422
    assert fake_app_instance.saved == []


@pytest.mark.asyncio
async def test_unsubscribe_is_idempotent_and_normalizes_phone(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/unsubscribe",
            json={"channel": "whatsapp", "identifier": "591 700-00000"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "unsubscribed"
    assert fake_app_instance.unsubscribed == ["+59170000000"]


@pytest.mark.asyncio
async def test_unsubscribe_normalizes_email_without_stripping_dots(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/unsubscribe",
            json={"channel": "email", "identifier": " Persona.Name@Example.COM "},
        )

    assert response.status_code == 200
    assert fake_app_instance.unsubscribed == ["persona.name@example.com"]


@pytest.mark.asyncio
async def test_preview_uses_existing_summaries_without_generation(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/preview",
            json={"categories": ["economia"], "frequency": "diario"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_data"] is True
    assert payload["items"][0]["title"] == "Brief de prueba"
    assert fake_app_instance.preview_categories == [["economia"]]
