from datetime import date
from types import SimpleNamespace

import httpx
import pytest

import src.main as main_module
from src.main import app


class FakeCategoryCountsDatabase:
    def __init__(self):
        self.calls: list[dict] = []

    async def get_category_counts(self, *, view, target_date, fallback_to_latest):
        self.calls.append(
            {"view": view, "target_date": target_date, "fallback_to_latest": fallback_to_latest}
        )
        if view == "recolectadas":
            counts = {"economia": 5, "policiales": 0, "general": 2}
        else:
            counts = {"economia": 3, "general": 1}
        return {
            "counts": counts,
            "total": sum(counts.values()),
            "date": target_date,
            "requested_date": target_date,
            "is_fallback": False,
        }


@pytest.fixture
def fake_app_instance():
    original = main_module.app_instance
    db = FakeCategoryCountsDatabase()
    main_module.app_instance = SimpleNamespace(
        db=db, settings=SimpleNamespace(schedule_timezone="America/La_Paz")
    )
    try:
        yield db
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_category_counts_omits_zero_categories(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/news/category-counts",
            params={"view": "resumenes", "date": "2026-08-25"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 4
    assert payload["counts"] == [
        {"slug": "economia", "label": "Economia", "count": 3},
        {"slug": "general", "label": "General", "count": 1},
    ]
    assert fake_app_instance.calls == [
        {"view": "resumenes", "target_date": date(2026, 8, 25), "fallback_to_latest": False}
    ]


@pytest.mark.asyncio
async def test_category_counts_recolectadas_view_excludes_zero_count_category(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/news/category-counts",
            params={"view": "recolectadas", "date": "2026-08-25"},
        )

    assert response.status_code == 200
    slugs = [item["slug"] for item in response.json()["counts"]]
    assert "policiales" not in slugs
    assert slugs == ["economia", "general"]


@pytest.mark.asyncio
async def test_category_counts_rejects_future_date(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/news/category-counts",
            params={"date": "2099-01-01"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_category_counts_requires_db():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(db=None, settings=SimpleNamespace())
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/news/category-counts")
        assert response.status_code == 503
    finally:
        main_module.app_instance = original
