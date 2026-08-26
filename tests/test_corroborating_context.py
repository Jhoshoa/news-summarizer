from types import SimpleNamespace
from unittest.mock import patch

import pytest
import sentry_sdk

from src.main import NewsSummarizerApp


def _make_app(db=None):
    settings = SimpleNamespace(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
    )
    app = NewsSummarizerApp(settings)
    app.db = db
    return app


class FakeSiblingsDatabase:
    def __init__(self, siblings_by_cluster: dict):
        self.siblings_by_cluster = siblings_by_cluster
        self.calls: list[dict] = []

    async def get_story_sibling_articles(self, story_cluster_id, *, exclude_article_id, limit=4):
        self.calls.append(
            {"story_cluster_id": story_cluster_id, "exclude_article_id": exclude_article_id}
        )
        return self.siblings_by_cluster.get(story_cluster_id, [])


class RaisingDatabase:
    async def get_story_sibling_articles(self, story_cluster_id, *, exclude_article_id, limit=4):
        raise RuntimeError("db unavailable")


@pytest.mark.asyncio
async def test_attach_corroborating_articles_adds_siblings_from_same_cluster():
    db = FakeSiblingsDatabase(
        {"cluster-1": [{"title": "Otra fuente", "description": "detalle", "source": "MedioB"}]}
    )
    app = _make_app(db)
    articles = [{"id": 1, "story_cluster_id": "cluster-1", "title": "Original"}]

    await app._attach_corroborating_articles(articles)

    assert articles[0]["corroborating_articles"] == [
        {"title": "Otra fuente", "description": "detalle", "source": "MedioB"}
    ]
    assert db.calls == [{"story_cluster_id": "cluster-1", "exclude_article_id": 1}]


@pytest.mark.asyncio
async def test_attach_corroborating_articles_skips_when_no_cluster_id():
    db = FakeSiblingsDatabase({})
    app = _make_app(db)
    articles = [{"id": 1, "title": "Sin cluster"}]

    await app._attach_corroborating_articles(articles)

    assert "corroborating_articles" not in articles[0]
    assert db.calls == []


@pytest.mark.asyncio
async def test_attach_corroborating_articles_skips_when_no_siblings():
    db = FakeSiblingsDatabase({})
    app = _make_app(db)
    articles = [{"id": 1, "story_cluster_id": "cluster-1", "title": "Unico"}]

    await app._attach_corroborating_articles(articles)

    assert "corroborating_articles" not in articles[0]


@pytest.mark.asyncio
async def test_attach_corroborating_articles_degrades_gracefully_on_db_error():
    app = _make_app(RaisingDatabase())
    articles = [{"id": 1, "story_cluster_id": "cluster-1", "title": "Original"}]

    await app._attach_corroborating_articles(articles)

    assert "corroborating_articles" not in articles[0]


@pytest.mark.asyncio
async def test_attach_corroborating_articles_reports_db_error_to_sentry():
    app = _make_app(RaisingDatabase())
    articles = [{"id": 1, "story_cluster_id": "cluster-1", "title": "Original"}]

    with patch.object(sentry_sdk, "capture_exception") as mock_capture:
        await app._attach_corroborating_articles(articles)

    mock_capture.assert_called_once()
    assert isinstance(mock_capture.call_args.args[0], RuntimeError)


@pytest.mark.asyncio
async def test_attach_corroborating_articles_noop_without_db():
    app = _make_app(db=None)
    articles = [{"id": 1, "story_cluster_id": "cluster-1", "title": "Original"}]

    await app._attach_corroborating_articles(articles)

    assert "corroborating_articles" not in articles[0]
