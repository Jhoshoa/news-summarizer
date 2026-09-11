"""Tests for /admin/classification/* -- the internal endpoints a scheduled
external reviewer (see the classification-fixing work this session) uses to
find articles the classifier already flagged as dudosos and correct them,
without exposing raw database credentials to that reviewer.
"""

from types import SimpleNamespace

import httpx
import pytest

import src.main as main_module
from src.main import app

API_AUTH_KEY = "test-api-auth-key-value"


class FakeReviewDatabase:
    def __init__(self, articles=None):
        self.articles = {a["id"]: a for a in (articles or [])}
        self.corrections = []

    async def get_articles_needing_category_review(self, since_minutes, limit=50):
        return list(self.articles.values())[:limit]

    async def get_article_by_id(self, article_id):
        return self.articles.get(article_id)

    async def correct_article_category(self, article_id, new_category, *, reason, corrected_by):
        article = self.articles.get(article_id)
        if not article:
            return None
        article = dict(article)
        article["category"] = new_category
        raw_payload = dict(article.get("raw_payload") or {})
        raw_payload["category_manual_correction"] = {
            "reason": reason,
            "corrected_by": corrected_by,
            "new_category": new_category,
        }
        article["raw_payload"] = raw_payload
        self.articles[article_id] = article
        self.corrections.append((article_id, new_category, reason, corrected_by))
        return article


def _article(article_id, category="deportes", **raw_payload_extra):
    raw_payload = {
        "category_method": "rules_low_confidence",
        "category_reason": "deportes:score=2;margin=2",
        "category_confidence": 0.6,
        "category_scores": {"deportes": 2.0, "politica": 0.0},
        **raw_payload_extra,
    }
    return {
        "id": article_id,
        "title": f"Articulo {article_id}",
        "description": "Descripcion de prueba",
        "content": None,
        "url": f"https://example.com/{article_id}",
        "source": "ElDeber",
        "category": category,
        "published_at": "2026-09-09T16:10:00",
        "collected_at": "2026-09-09T19:01:51",
        "raw_payload": raw_payload,
    }


@pytest.fixture
def fake_app_instance():
    original = main_module.app_instance
    db = FakeReviewDatabase(
        [
            _article(5414, category="deportes", category_llm_error="ai_fallback_batch_limit_reached"),
            _article(5471, category="deportes", category_llm_error="Expecting ',' delimiter"),
        ]
    )
    main_module.app_instance = SimpleNamespace(
        db=db,
        settings=SimpleNamespace(api_auth_key=API_AUTH_KEY),
    )
    try:
        yield db
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_review_queue_rejects_missing_api_key(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/admin/classification/review-queue")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_review_queue_returns_flagged_articles_with_valid_key(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/admin/classification/review-queue",
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    ids = {item["id"] for item in body["items"]}
    assert ids == {5414, 5471}
    assert body["items"][0]["category_method"] == "rules_low_confidence"


@pytest.mark.asyncio
async def test_review_queue_clamps_since_minutes_and_limit(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/admin/classification/review-queue",
            params={"since_minutes": 999999, "limit": 999},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_correct_category_rejects_missing_api_key(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/admin/classification/correct",
            json={"article_id": 5414, "category": "policiales", "reason": "test"},
        )

    assert response.status_code == 401
    assert fake_app_instance.corrections == []


@pytest.mark.asyncio
async def test_correct_category_applies_correction_with_audit_trail(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/admin/classification/correct",
            json={
                "article_id": 5414,
                "category": "policiales",
                "reason": "Regimiento Bolivar -- altercado militar, no deportes",
                "corrected_by": "claude_scheduled_review",
            },
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "corrected"
    assert body["previous_category"] == "deportes"
    assert body["category"] == "policiales"

    assert fake_app_instance.corrections == [
        (5414, "policiales", "Regimiento Bolivar -- altercado militar, no deportes", "claude_scheduled_review")
    ]


@pytest.mark.asyncio
async def test_correct_category_rejects_unknown_category(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/admin/classification/correct",
            json={"article_id": 5414, "category": "gastronomia", "reason": "test"},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 422
    assert fake_app_instance.corrections == []


@pytest.mark.asyncio
async def test_correct_category_returns_404_for_unknown_article(fake_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/admin/classification/correct",
            json={"article_id": 999999, "category": "policiales", "reason": "test"},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 404
