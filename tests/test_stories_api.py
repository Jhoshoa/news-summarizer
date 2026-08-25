from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest

import src.main as main_module
from src.main import app


class FakeStoriesDatabase:
    def __init__(self):
        self.list_calls: list[dict] = []
        self.stories: dict[str, dict] = {}
        self.corrections: list[dict] = []
        self.publication_calls: list[dict] = []

    async def list_stories(self, *, category, min_sources, page, page_size):
        self.list_calls.append(
            {"category": category, "min_sources": min_sources, "page": page, "page_size": page_size}
        )
        return (
            [
                {
                    "id": "cluster-1",
                    "canonical_title": "Gobierno anuncia nuevo precio de combustibles",
                    "category": "economia",
                    "country": "BO",
                    "current_status": "developing",
                    "confidence": {"level": "multi_source", "label": "Confirmado por varias fuentes"},
                    "first_published_at": datetime(2026, 8, 24, 10, 0),
                    "last_updated_at": datetime(2026, 8, 24, 12, 0),
                    "article_count": 3,
                    "source_count": 2,
                }
            ],
            1,
        )

    async def get_story(self, story_id):
        return self.stories.get(story_id)

    async def add_story_correction(self, story_id, *, reason, corrected_by=None):
        if story_id not in self.stories and story_id != "cluster-1":
            return None
        self.corrections.append(
            {"story_id": story_id, "reason": reason, "corrected_by": corrected_by}
        )
        return {
            "id": len(self.corrections),
            "story_id": story_id,
            "reason": reason,
            "corrected_by": corrected_by,
            "corrected_at": datetime(2026, 8, 24, 13, 0),
        }

    async def set_story_publication_status(self, story_id, *, unpublished):
        if story_id not in self.stories and story_id != "cluster-1":
            return False
        self.publication_calls.append({"story_id": story_id, "unpublished": unpublished})
        return True


@pytest.fixture
def fake_app_instance():
    original = main_module.app_instance
    db = FakeStoriesDatabase()
    main_module.app_instance = SimpleNamespace(
        db=db, settings=SimpleNamespace(api_auth_key="test-key")
    )
    try:
        yield db
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_list_stories_returns_paginated_items(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/stories", params={"category": "economia", "page": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["page"] == 2
    assert payload["items"][0]["id"] == "cluster-1"
    assert payload["items"][0]["confidence"] == {
        "level": "multi_source",
        "label": "Confirmado por varias fuentes",
    }
    assert fake_app_instance.list_calls == [
        {"category": "economia", "min_sources": 1, "page": 2, "page_size": 20}
    ]


@pytest.mark.asyncio
async def test_list_stories_requires_db():
    original = main_module.app_instance
    main_module.app_instance = SimpleNamespace(db=None, settings=SimpleNamespace())
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/stories")
    finally:
        main_module.app_instance = original

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_get_story_returns_articles_with_relationship_type(fake_app_instance):
    fake_app_instance.stories["cluster-1"] = {
        "id": "cluster-1",
        "canonical_title": "Gobierno anuncia nuevo precio de combustibles",
        "short_summary": None,
        "detailed_summary": None,
        "category": "economia",
        "country": "BO",
        "current_status": "developing",
        "first_published_at": datetime(2026, 8, 24, 10, 0),
        "last_updated_at": datetime(2026, 8, 24, 12, 0),
        "article_count": 2,
        "source_count": 2,
        "articles": [
            {
                "article_id": 1,
                "title": "Gobierno anuncia modificacion",
                "url": "https://a.com/1",
                "source": "MedioA",
                "published_at": datetime(2026, 8, 24, 10, 0),
                "relationship_type": "original_report",
                "similarity_score": None,
            },
            {
                "article_id": 2,
                "title": "Nuevo precio entra en vigencia",
                "url": "https://b.com/2",
                "source": "MedioB",
                "published_at": datetime(2026, 8, 24, 12, 0),
                "relationship_type": "duplicate",
                "similarity_score": 0.91,
            },
        ],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/stories/cluster-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["article_count"] == 2
    assert len(payload["articles"]) == 2
    assert payload["articles"][1]["relationship_type"] == "duplicate"


@pytest.mark.asyncio
async def test_get_story_returns_404_when_not_found(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/stories/does-not-exist")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_correction_requires_valid_api_key(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        no_key = await client.post(
            "/api/stories/cluster-1/corrections", json={"reason": "dato erroneo"}
        )
        wrong_key = await client.post(
            "/api/stories/cluster-1/corrections",
            json={"reason": "dato erroneo"},
            headers={"X-API-Key": "wrong"},
        )

    assert no_key.status_code == 401
    assert wrong_key.status_code == 401
    assert fake_app_instance.corrections == []


@pytest.mark.asyncio
async def test_add_correction_succeeds_with_valid_api_key(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/stories/cluster-1/corrections",
            json={"reason": "la cifra correcta es 24.6 millones", "corrected_by": "editor@ecobrief.bo"},
            headers={"X-API-Key": "test-key"},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["reason"] == "la cifra correcta es 24.6 millones"
    assert fake_app_instance.corrections == [
        {
            "story_id": "cluster-1",
            "reason": "la cifra correcta es 24.6 millones",
            "corrected_by": "editor@ecobrief.bo",
        }
    ]


@pytest.mark.asyncio
async def test_add_correction_returns_404_for_unknown_story(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/stories/does-not-exist/corrections",
            json={"reason": "x"},
            headers={"X-API-Key": "test-key"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unpublish_and_republish_require_valid_api_key(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        unpublish_no_key = await client.post("/api/stories/cluster-1/unpublish")
        republish_no_key = await client.post("/api/stories/cluster-1/republish")

    assert unpublish_no_key.status_code == 401
    assert republish_no_key.status_code == 401
    assert fake_app_instance.publication_calls == []


@pytest.mark.asyncio
async def test_unpublish_and_republish_succeed_with_valid_api_key(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        unpublish = await client.post(
            "/api/stories/cluster-1/unpublish", headers={"X-API-Key": "test-key"}
        )
        republish = await client.post(
            "/api/stories/cluster-1/republish", headers={"X-API-Key": "test-key"}
        )

    assert unpublish.status_code == 200
    assert unpublish.json()["current_status"] == "unpublished"
    assert republish.status_code == 200
    assert fake_app_instance.publication_calls == [
        {"story_id": "cluster-1", "unpublished": True},
        {"story_id": "cluster-1", "unpublished": False},
    ]
