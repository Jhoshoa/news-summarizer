from types import SimpleNamespace

import httpx
import pytest

import src.main as main_module
from src.main import app


class FakeAnalyticsDatabase:
    def __init__(self):
        self.recorded: list[dict] = []
        self.fail_on_record = False

    async def record_events(self, events):
        if self.fail_on_record:
            raise RuntimeError("db down")
        self.recorded.extend(events)
        return len(events)

    async def get_analytics_summary(self, since):
        return {
            "since": since,
            "event_counts": {"brief_opened": 3},
            "unique_sessions": 2,
            "unique_users": 1,
        }


@pytest.fixture
def fake_app_instance():
    original = main_module.app_instance
    db = FakeAnalyticsDatabase()
    main_module.app_instance = SimpleNamespace(
        db=db,
        settings=SimpleNamespace(api_auth_key="test-key"),
    )
    try:
        yield db
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_ingest_events_accepts_valid_batch(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/analytics/events",
            json={
                "events": [
                    {"event_name": "brief_opened", "session_id": "s1", "category": "economia"},
                    {"event_name": "story_opened", "session_id": "s1", "story_id": "abc123"},
                ]
            },
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload == {"accepted": 2, "skipped": 0}
    assert len(fake_app_instance.recorded) == 2
    assert fake_app_instance.recorded[0]["event_name"] == "brief_opened"


@pytest.mark.asyncio
async def test_ingest_events_drops_unknown_event_names_without_failing_batch(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/analytics/events",
            json={
                "events": [
                    {"event_name": "brief_opened", "session_id": "s1"},
                    {"event_name": "totally_made_up_event", "session_id": "s1"},
                ]
            },
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload == {"accepted": 1, "skipped": 1}
    assert len(fake_app_instance.recorded) == 1


@pytest.mark.asyncio
async def test_ingest_events_rejects_empty_batch(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/analytics/events", json={"events": []})

    assert response.status_code == 422
    assert fake_app_instance.recorded == []


@pytest.mark.asyncio
async def test_ingest_events_never_500s_when_db_write_fails(fake_app_instance):
    fake_app_instance.fail_on_record = True
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/analytics/events",
            json={"events": [{"event_name": "brief_opened", "session_id": "s1"}]},
        )

    assert response.status_code == 202
    assert response.json() == {"accepted": 0, "skipped": 1}


@pytest.mark.asyncio
async def test_ingest_events_returns_zero_when_db_unavailable():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(db=None, settings=SimpleNamespace())
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/analytics/events",
                json={"events": [{"event_name": "brief_opened"}]},
            )
    finally:
        main_module.app_instance = original

    assert response.status_code == 202
    assert response.json() == {"accepted": 0, "skipped": 1}


@pytest.mark.asyncio
async def test_summary_requires_valid_api_key(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/analytics/summary")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_summary_returns_counts_with_valid_api_key(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/analytics/summary", headers={"X-API-Key": "test-key"}
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["event_counts"] == {"brief_opened": 3}
    assert payload["unique_sessions"] == 2
    assert payload["unique_users"] == 1
