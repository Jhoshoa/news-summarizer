from types import SimpleNamespace

import pytest

from src.main import NewsSummarizerApp


class FakeDatabase:
    def __init__(self):
        self.upserted_articles = []
        self.saved_summaries = []
        self.finished_runs = []

    async def get_recent_summaries(self, categories):
        return []

    async def get_recent_articles(self, categories, since, limit=None):
        return []

    async def start_collection_run(self, requested_categories):
        return 123

    async def upsert_articles(self, articles):
        self.upserted_articles = articles
        for index, article in enumerate(articles, 1):
            article["id"] = index
        return {"inserted": len(articles), "updated": 0}

    async def finish_collection_run(self, run_id, **kwargs):
        self.finished_runs.append({"run_id": run_id, **kwargs})

    async def save_summaries(self, summaries, *, llm_provider=None, llm_model=None):
        self.saved_summaries = summaries
        return {"inserted": len(summaries), "updated": 0}

    async def get_active_subscribers(self):
        return []


class FakeLLM:
    provider = "fake"
    models = {"quality": "fake-quality"}

    async def chat(self, prompt, **kwargs):
        if prompt.startswith("Reescribe"):
            return "1. Titulo reescrito | Resumen reescrito"

        return """
        [
          {
            "article_id": 1,
            "title": "Titulo resumido",
            "summary": "Resumen claro de la noticia.",
            "fact": "Dato clave",
            "category": "politica"
          }
        ]
        """


@pytest.mark.asyncio
async def test_fresh_collection_is_classified_persisted_and_summarized():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
    )
    db = FakeDatabase()
    app = NewsSummarizerApp(settings)
    app.db = db
    app.llm = FakeLLM()

    async def collect_news(categories):
        return (
            [
                {
                    "title": "Presidente anuncia nueva medida",
                    "url": "https://example.com/noticia",
                    "description": "",
                    "content": "El gobierno y el presidente anunciaron una decision politica importante.",
                    "source": "Example",
                    "source_type": "scraper",
                    "source_url": "https://example.com/",
                    "category": "general",
                    "hash": "abc",
                }
            ],
            {"scraper": 1, "newsapi": 0, "inserted": 0, "updated": 0},
            123,
        )

    app._collect_news = collect_news

    result = await app.send_summaries("manual", refresh=True)

    assert result["collected"] == 1
    assert result["summaries"] == 1
    assert db.upserted_articles[0]["category"] == "politica"
    assert db.upserted_articles[0]["content"]
    assert db.saved_summaries[0]["article_id"] == 1
    assert db.finished_runs[0]["status"] == "success"


@pytest.mark.asyncio
async def test_fresh_collection_skips_title_only_articles():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
    )
    db = FakeDatabase()
    app = NewsSummarizerApp(settings)
    app.db = db
    app.llm = FakeLLM()

    async def collect_news(categories):
        return (
            [
                {
                    "title": "Ley Integral contra la Trata y Trafico de Personas",
                    "url": "https://example.com/ley-integral",
                    "description": "",
                    "content": "",
                    "source": "RedBolivision",
                    "source_type": "scraper",
                    "source_url": "https://example.com/",
                    "category": "general",
                    "hash": "abc",
                }
            ],
            {"scraper": 1, "newsapi": 0, "inserted": 0, "updated": 0},
            123,
        )

    app._collect_news = collect_news

    result = await app.send_summaries("manual", refresh=True)

    assert result["collected"] == 0
    assert result["summaries"] == 0
    assert db.upserted_articles == []
    assert db.saved_summaries == []
    assert db.finished_runs[0]["status"] == "partial"
