from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import src.main as main_module
from src.db.repository import Base, Database
from src.db.telegram_links import TelegramLinkRepository
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
            whatsapp_meta_access_token=None,
            whatsapp_meta_phone_number_id=None,
            email_enabled=False,
        ),
    )
    try:
        yield db
    finally:
        main_module.app_instance = original


class FakeTelegram:
    def __init__(self, username: str | None = "EcoBriefBoliviaBot", bot: bool = True):
        self.bot = bot
        self._username = username

    async def get_username(self):
        return self._username


@pytest.fixture
async def fake_app_instance_with_telegram():
    """Como fake_app_instance, pero con Telegram "configurado" y un `db.session_maker`
    real (sqlite en memoria) para que /telegram/link pueda usar TelegramLinkRepository."""

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db = object.__new__(Database)
    db.engine = engine
    db.session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        db=db,
        telegram=FakeTelegram(),
        settings=SimpleNamespace(
            summary_candidates_per_category=8,
            summary_candidates_extended_limit=8,
            summary_candidates_extended_categories="politica, economia",
            telegram_bot_token="fake-token",
            whatsapp_meta_access_token=None,
            whatsapp_meta_phone_number_id=None,
            email_enabled=False,
        ),
    )
    try:
        yield db
    finally:
        main_module.app_instance = original
        await engine.dispose()


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
    frequency_notes = {item["slug"]: item["note"] for item in payload["frequencies"]}
    assert frequency_notes["diario"] is None
    assert frequency_notes["dias_habiles"] is None
    assert frequency_notes["tres_veces_semana"] == "Se envia lunes, miercoles y viernes."
    assert frequency_notes["semanal"] == "Se envia los lunes."
    assert {item["slug"] for item in payload["preferred_hours"]} == {str(hour) for hour in range(9, 24)}
    assert {"slug": "9", "label": "09:00", "enabled": True, "note": None} in payload["preferred_hours"]


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
                "preferred_hour": 9,
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
            "preferred_hour": 9,
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
    # domain_can_receive_mail hace una consulta DNS real -- se mockea para que
    # el test no dependa de la red ni de que example.com siga resolviendo.
    with patch("src.api.preferences.domain_can_receive_mail", return_value=True) as mock_check:
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/preferences/subscribe",
                json={
                    "channel": "email",
                    "email": " Persona@Example.COM ",
                    "categories": ["general"],
                    "frequency": "semanal",
                    "preferred_hour": 20,
                    "timezone": "America/La_Paz",
                    "consent_accepted": True,
                },
            )

    assert response.status_code == 200
    mock_check.assert_called_once_with("example.com")
    assert fake_app_instance.saved == [
        {
            "phone": None,
            "telegram_id": None,
            "email": "persona@example.com",
            "channel": "email",
            "categories": {"general"},
            "frequency": "semanal",
            "preferred_hour": 20,
            "timezone": "America/La_Paz",
            "consent_accepted": True,
        }
    ]


@pytest.mark.asyncio
async def test_subscribe_rejects_email_whose_domain_cannot_receive_mail(fake_app_instance):
    """Ej. test@test.cadfa -- formato valido pero el dominio no existe."""

    transport = httpx.ASGITransport(app=app)
    with patch("src.api.preferences.domain_can_receive_mail", return_value=False) as mock_check:
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/preferences/subscribe",
                json={
                    "channel": "email",
                    "email": "test@test.cadfa",
                    "categories": ["general"],
                    "consent_accepted": True,
                },
            )

    assert response.status_code == 422
    mock_check.assert_called_once_with("test.cadfa")
    assert fake_app_instance.saved == []


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
async def test_subscribe_rejects_preferred_hour_outside_9_23(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/subscribe",
            json={
                "channel": "whatsapp",
                "phone": "+59170000000",
                "categories": ["economia"],
                "preferred_hour": 6,
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


class FakeFlakyDatabase:
    """Simulates a DB connection that was fine at startup (app_instance.db is
    set) but drops mid-request -- e.g. the real [WinError 121] "semaphore
    timeout" seen in production when a query tries to open a fresh
    connection to a remote Postgres and the network hiccups. Regression
    test for that Sentry-reported crash: the endpoint used to let this
    propagate as a raw unhandled 500."""

    async def save_subscription(self, **kwargs):
        raise OSError("[WinError 121] The semaphore timeout period has expired")

    async def unsubscribe(self, identifier):
        raise OSError("[WinError 121] The semaphore timeout period has expired")

    async def get_preference_preview(self, categories):
        raise OSError("[WinError 121] The semaphore timeout period has expired")


@pytest.fixture
def flaky_app_instance():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        db=FakeFlakyDatabase(),
        settings=SimpleNamespace(
            summary_candidates_per_category=8,
            summary_candidates_extended_limit=8,
            summary_candidates_extended_categories="politica, economia",
            telegram_bot_token=None,
            whatsapp_meta_access_token=None,
            whatsapp_meta_phone_number_id=None,
            email_enabled=False,
        ),
    )
    try:
        yield
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_preview_returns_503_instead_of_a_raw_500_when_db_connection_drops(
    flaky_app_instance,
):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/preview",
            json={"categories": ["economia"], "frequency": "diario"},
        )

    assert response.status_code == 503
    assert "base de datos" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_subscribe_returns_503_instead_of_a_raw_500_when_db_connection_drops(
    flaky_app_instance,
):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/subscribe",
            json={
                "channel": "whatsapp",
                "phone": "+59170000000",
                "categories": ["economia"],
                "consent_accepted": True,
            },
        )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_unsubscribe_returns_503_instead_of_a_raw_500_when_db_connection_drops(
    flaky_app_instance,
):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/unsubscribe",
            json={"channel": "whatsapp", "identifier": "+59170000000"},
        )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_create_telegram_link_returns_deep_link_with_token(fake_app_instance_with_telegram):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/telegram/link",
            json={"categories": ["economia", "deportes"], "consent_accepted": True},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["bot_username"] == "EcoBriefBoliviaBot"
    assert payload["deep_link"] == f"https://t.me/EcoBriefBoliviaBot?start={payload['token']}"
    assert payload["expires_in_seconds"] == 600
    assert payload["token"]


@pytest.mark.asyncio
async def test_create_telegram_link_always_uses_fixed_frequency_and_hour(
    fake_app_instance_with_telegram,
):
    """Telegram no deja elegir frecuencia/hora en el formulario -- el push
    queda fijo en diario/9am, y el bot cubre lo demas con /noticias."""

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/telegram/link",
            # un cliente que ignore el tipo (o alguien pegandole directo a la
            # API) no deberia poder colarse una frecuencia/hora distinta
            json={
                "categories": ["economia"],
                "frequency": "semanal",
                "preferred_hour": 20,
                "consent_accepted": True,
            },
        )

    token = response.json()["token"]
    repo = TelegramLinkRepository(fake_app_instance_with_telegram.session_maker)
    preferences = await repo.consume_link(token)

    assert preferences["frequency"] == "diario"
    assert preferences["preferred_hour"] == 9


@pytest.mark.asyncio
async def test_create_telegram_link_rejects_missing_consent(fake_app_instance_with_telegram):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/telegram/link",
            json={"categories": ["economia"], "consent_accepted": False},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_telegram_link_rejects_invalid_category(fake_app_instance_with_telegram):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/telegram/link",
            json={"categories": ["no-existe"], "consent_accepted": True},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_telegram_link_returns_503_when_telegram_not_configured(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/preferences/telegram/link",
            json={"categories": ["economia"], "consent_accepted": True},
        )

    assert response.status_code == 503
