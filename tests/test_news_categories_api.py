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
async def test_category_counts_defaults_to_resumenes_view(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.get("/api/news/category-counts", params={"date": "2026-08-25"})

    assert fake_app_instance.calls[0]["view"] == "resumenes"


@pytest.mark.asyncio
async def test_category_counts_rejects_invalid_view():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        db=FakeCategoryCountsDatabase(), settings=SimpleNamespace(schedule_timezone="America/La_Paz")
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/api/news/category-counts", params={"view": "no-existe"}
            )
        assert response.status_code == 422
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_category_counts_orders_results_by_default_categories_not_by_raw_dict_order(
    fake_app_instance,
):
    class ReverseOrderDatabase:
        async def get_category_counts(self, *, view, target_date, fallback_to_latest):
            return {
                "counts": {"policiales": 1, "deportes": 1, "economia": 1},
                "total": 3,
                "date": target_date,
                "requested_date": target_date,
                "is_fallback": False,
            }

    main_module.app_instance = SimpleNamespace(
        db=ReverseOrderDatabase(), settings=SimpleNamespace(schedule_timezone="America/La_Paz")
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/news/category-counts", params={"date": "2026-08-25"})

    slugs = [item["slug"] for item in response.json()["counts"]]
    assert slugs == ["economia", "deportes", "policiales"]


@pytest.mark.asyncio
async def test_category_counts_passes_through_fallback_metadata(fake_app_instance):
    class FallbackDatabase:
        async def get_category_counts(self, *, view, target_date, fallback_to_latest):
            return {
                "counts": {"economia": 4},
                "total": 4,
                "date": date(2026, 8, 20),
                "requested_date": target_date,
                "is_fallback": True,
            }

    main_module.app_instance = SimpleNamespace(
        db=FallbackDatabase(), settings=SimpleNamespace(schedule_timezone="America/La_Paz")
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/news/category-counts",
            params={"date": "2026-08-25", "fallback_to_latest": "true"},
        )

    payload = response.json()
    assert payload["is_fallback"] is True
    assert payload["date"] == "2026-08-20"
    assert payload["requested_date"] == "2026-08-25"


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


@pytest.mark.asyncio
async def test_category_counts_returns_503_instead_of_a_raw_500_when_db_connection_drops():
    class FlakyDatabase:
        async def get_category_counts(self, **kwargs):
            raise OSError("[WinError 121] The semaphore timeout period has expired")

    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(
        db=FlakyDatabase(), settings=SimpleNamespace(schedule_timezone="America/La_Paz")
    )
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/news/category-counts")
        assert response.status_code == 503
    finally:
        main_module.app_instance = original
