from types import SimpleNamespace

import httpx
import pytest

import src.api.economic_indicators as economic_module
import src.main as main_module
from src.main import app

API_AUTH_KEY = "test-api-auth-key-value"


@pytest.fixture
def fake_summary_app_instance():
    original = main_module.app_instance
    calls = []

    async def send_summaries(time_of_day="manual", refresh=False):
        calls.append((time_of_day, refresh))
        return {
            "collected": 4,
            "processed": 3,
            "summaries": 2,
            "sent": 1,
        }

    main_module.app_instance = SimpleNamespace(
        settings=SimpleNamespace(api_auth_key=API_AUTH_KEY),
        send_summaries=send_summaries,
    )
    try:
        yield calls
    finally:
        main_module.app_instance = original


@pytest.fixture
def fake_economic_app_instance(monkeypatch):
    original = main_module.app_instance

    class FakeCollector:
        def __init__(self, timeout):
            self.timeout = timeout

        async def fetch_all(self):
            return [
                {
                    "source": "bcb",
                    "indicator_code": "bcb_unidad_de_fomento_a_la_vivienda_ufv",
                    "indicator_name": "UFV",
                    "indicator_group": "Unidad de fomento a la vivienda",
                    "value": "3.27232",
                }
            ]

    class FakeRepository:
        def __init__(self, session_maker):
            self.session_maker = session_maker

        async def save_values(self, indicators):
            return {"inserted": len(indicators), "unchanged": 0, "skipped": 0}

        async def get_latest_values(self, target_date=None):
            return [{"indicator_code": "bcb_unidad_de_fomento_a_la_vivienda_ufv", "value": 3.27232}]

    monkeypatch.setattr(economic_module, "EconomicIndicatorCollector", FakeCollector)
    monkeypatch.setattr(economic_module, "EconomicIndicatorRepository", FakeRepository)

    main_module.app_instance = SimpleNamespace(
        db=SimpleNamespace(session_maker=object()),
        settings=SimpleNamespace(api_auth_key=API_AUTH_KEY, scraper_timeout=30),
    )
    try:
        yield
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_trigger_summary_rejects_missing_cron_key(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/trigger/summary", params={"refresh": "true"})

    assert response.status_code == 401
    assert fake_summary_app_instance == []


@pytest.mark.asyncio
async def test_trigger_summary_accepts_valid_cron_key(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/trigger/summary",
            params={"refresh": "true", "time_of_day": "manual"},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200
    assert response.json()["result"]["summaries"] == 2
    assert fake_summary_app_instance == [("manual", True)]


@pytest.mark.asyncio
async def test_economic_refresh_rejects_missing_cron_key(fake_economic_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/economic-indicators/refresh")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_economic_refresh_accepts_valid_cron_key(fake_economic_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/economic-indicators/refresh",
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["collected"] == 1
    assert payload["inserted"] == 1


def test_private_refresh_endpoints_document_cron_header():
    schema = app.openapi()
    for path in ("/api/economic-indicators/refresh", "/trigger/summary"):
        parameters = schema["paths"][path]["post"]["parameters"]
        cron_header = next(param for param in parameters if param["name"] == "X-API-Key")
        assert cron_header["in"] == "header"
        assert cron_header["required"] is False
