from datetime import date
from types import SimpleNamespace

import httpx
import pytest

import src.main as main_module
from src.main import app


class FakeImpactDatabase:
    def __init__(self):
        self.calls = []

    async def get_impact_metrics(self, metrics_date, *, fallback_to_latest=True):
        self.calls.append((metrics_date, fallback_to_latest))
        effective_date = date(2026, 6, 2) if fallback_to_latest else metrics_date
        return {
            "date": effective_date,
            "requested_date": metrics_date,
            "is_fallback": effective_date != metrics_date,
            "has_data": True,
            "collected_articles": 10,
            "unique_articles": 8,
            "summaries": 3,
            "duplicate_articles_estimated": 2,
            "reduction_rate": 0.7,
            "estimated_pages_avoided": 7,
            "estimated_minutes_saved": 3.5,
            "estimated_data_saved_mb": 5.6,
            "cache_reused": False,
            "ai_calls_avoided_estimated": 2,
            "pipeline": [
                {"label": "Recolectadas", "value": 10},
                {"label": "Unicas", "value": 8},
                {"label": "Briefs", "value": 3},
            ],
            "methodology": {
                "minutes_per_article": 0.5,
                "mb_per_page": 0.8,
                "note": "Estimaciones orientativas basadas en articulos evitados.",
            },
        }


@pytest.fixture
def fake_app_instance():
    original = main_module.app_instance
    db = FakeImpactDatabase()
    main_module.app_instance = SimpleNamespace(
        db=db,
        settings=SimpleNamespace(
            schedule_timezone="America/Caracas",
            summary_candidates_extended_limit=8,
            summary_candidates_extended_categories="politica, economia",
            summary_candidates_per_category=8,
        ),
    )
    try:
        yield db
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_impact_metrics_endpoint_returns_previous_day_when_fallback_applies(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/impact-metrics", params={"date": "2026-06-03"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2026-06-02"
    assert payload["requested_date"] == "2026-06-03"
    assert payload["is_fallback"] is True
    assert payload["has_data"] is True
    assert payload["pipeline"][0] == {"label": "Recolectadas", "value": 10}
    assert fake_app_instance.calls == [(date(2026, 6, 3), True)]


@pytest.mark.asyncio
async def test_impact_metrics_endpoint_can_disable_fallback(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/impact-metrics",
            params={"date": "2026-06-03", "fallback_to_latest": "false"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2026-06-03"
    assert payload["requested_date"] == "2026-06-03"
    assert payload["is_fallback"] is False
    assert fake_app_instance.calls == [(date(2026, 6, 3), False)]


@pytest.mark.asyncio
async def test_impact_metrics_endpoint_rejects_future_dates(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/impact-metrics", params={"date": "2999-01-01"})

    assert response.status_code == 422
    assert response.json()["detail"] == "La fecha no puede ser futura"
    assert fake_app_instance.calls == []
