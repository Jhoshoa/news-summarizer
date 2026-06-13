from datetime import datetime
from types import SimpleNamespace

import pytest

from src.main import NewsSummarizerApp


class FakeDatabase:
    def __init__(self):
        self.upserted_articles = []
        self.saved_summaries = []
        self.finished_runs = []

    async def get_recent_summaries(self, categories, summary_date=None):
        return []

    async def get_recent_articles(self, categories, since, limit=None):
        return []

    async def start_collection_run(self, requested_categories):
        return 123

    async def upsert_articles(self, articles):
        self.upserted_articles = articles
        for index, article in enumerate(articles, 1):
            article["id"] = index
        return {"inserted": len(articles), "updated": 0, "historical_duplicates": 0}

    async def finish_collection_run(self, run_id, **kwargs):
        self.finished_runs.append({"run_id": run_id, **kwargs})

    async def save_summaries(
        self,
        summaries,
        *,
        llm_provider=None,
        llm_model=None,
        summary_date=None,
    ):
        self.saved_summaries = summaries
        self.saved_summary_date = summary_date
        return {"inserted": len(summaries), "updated": 0}

    async def get_active_subscribers(self):
        return []


class CacheFailingDatabase(FakeDatabase):
    async def get_recent_summaries(self, categories, summary_date=None):
        raise RuntimeError("schema cache read failed")


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


class CachedSummaryDatabase(FakeDatabase):
    def __init__(self, summaries, subscribers):
        super().__init__()
        self.summaries = summaries
        self.subscribers = subscribers

    async def get_recent_summaries(self, categories, summary_date=None):
        self.requested_summary_date = summary_date
        return self.summaries

    async def get_active_subscribers(self):
        return self.subscribers


class FakeWhatsApp:
    def __init__(self):
        self.sent = []

    def send_message(self, phone, message):
        self.sent.append((phone, message))
        return True


class FakeTelegram:
    def __init__(self):
        self.sent = []

    async def send_message(self, telegram_id, message):
        self.sent.append((telegram_id, message))
        return True


class FakeEmail:
    def __init__(self):
        self.sent = []

    async def send_message(self, email, subject, body, html_body=None):
        self.sent.append((email, subject, body, html_body))
        return True


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
    assert db.finished_runs[0]["raw_collected_count"] == 1
    assert db.finished_runs[0]["usable_count"] == 1
    assert db.finished_runs[0]["quality_dropped_count"] == 0
    assert db.finished_runs[0]["deduplicated_count"] == 1
    assert db.finished_runs[0]["duplicate_dropped_count"] == 0
    assert db.finished_runs[0]["ranked_count"] == 1
    assert db.finished_runs[0]["summary_candidates_count"] == 1
    assert db.finished_runs[0]["summaries_count"] == 1


@pytest.mark.asyncio
async def test_refresh_collects_fresh_news_when_cache_db_read_fails():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
    )
    db = CacheFailingDatabase()
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
                    "category": "politica",
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
    assert db.finished_runs[0]["metrics_payload"]["cache_db_error"] == "schema cache read failed"


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
    assert db.finished_runs[0]["raw_collected_count"] == 1
    assert db.finished_runs[0]["usable_count"] == 0
    assert db.finished_runs[0]["quality_dropped_count"] == 1
    assert db.finished_runs[0]["deduplicated_count"] == 0
    assert db.finished_runs[0]["summaries_count"] == 0


def test_summary_candidates_are_diversified_by_source_within_category():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
    )
    app = NewsSummarizerApp(settings)
    news = [
        {"title": "Unitel 1", "category": "politica", "source": "Unitel", "score": 0.9},
        {"title": "Unitel 2", "category": "politica", "source": "Unitel", "score": 0.89},
        {"title": "Unitel 3", "category": "politica", "source": "Unitel", "score": 0.88},
        {"title": "Unitel 4", "category": "politica", "source": "Unitel", "score": 0.87},
        {"title": "RedUno 1", "category": "politica", "source": "RedUno", "score": 0.8},
        {"title": "RadioFides 1", "category": "politica", "source": "RadioFides", "score": 0.78},
    ]

    selected = app._select_summary_candidates(news, ["politica"])

    assert [article["title"] for article in selected] == [
        "Unitel 1",
        "Unitel 2",
        "RedUno 1",
        "RadioFides 1",
        "Unitel 3",
    ]


def test_summary_candidates_do_not_drop_articles_when_only_one_source_exists():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
    )
    app = NewsSummarizerApp(settings)
    news = [
        {"title": f"Unitel {index}", "category": "politica", "source": "Unitel", "score": 1 - index}
        for index in range(1, 7)
    ]

    selected = app._select_summary_candidates(news, ["politica"])

    assert [article["title"] for article in selected] == [
        "Unitel 1",
        "Unitel 2",
        "Unitel 3",
        "Unitel 4",
        "Unitel 5",
    ]


def test_summary_candidates_exclude_historical_duplicates_and_repeated_clusters():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
    )
    app = NewsSummarizerApp(settings)
    news = [
        {
            "title": "Canonica",
            "category": "politica",
            "source": "Unitel",
            "story_cluster_id": "story-1",
            "score": 0.9,
        },
        {
            "title": "Duplicada historica",
            "category": "politica",
            "source": "RedUno",
            "story_cluster_id": "story-1",
            "duplicate_of_article_id": 1,
            "score": 0.8,
        },
        {
            "title": "Otra cobertura misma historia",
            "category": "politica",
            "source": "RadioFides",
            "story_cluster_id": "story-1",
            "score": 0.7,
        },
        {
            "title": "Historia nueva",
            "category": "politica",
            "source": "RedUno",
            "story_cluster_id": "story-2",
            "score": 0.6,
        },
    ]

    selected = app._select_summary_candidates(news, ["politica"])

    assert [article["title"] for article in selected] == ["Canonica", "Historia nueva"]


def test_delivery_summaries_are_deduplicated_by_normalized_title():
    settings = SimpleNamespace(
        categories_list=["deportes"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
    )
    app = NewsSummarizerApp(settings)
    summaries = [
        {
            "title": "Video: Reportera cae al intentar atrapar regalo",
            "summary": "Primer resumen.",
            "category": "deportes",
        },
        {
            "title": " video reportera cae al intentar atrapar regalo ",
            "summary": "Segundo resumen duplicado.",
            "category": "deportes",
        },
        {
            "title": "Bolivia cayo ante Escocia",
            "summary": "Otra noticia.",
            "category": "deportes",
        },
    ]

    result = app._deduplicate_summaries_for_delivery(summaries)

    assert [summary["title"] for summary in result] == [
        "Video: Reportera cae al intentar atrapar regalo",
        "Bolivia cayo ante Escocia",
    ]


def test_summaries_are_deduplicated_by_story_cluster_for_storage_and_delivery():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
    )
    app = NewsSummarizerApp(settings)
    summaries = [
        {
            "title": "Titulo A",
            "summary": "Primer resumen.",
            "category": "politica",
            "story_cluster_id": "story-1",
        },
        {
            "title": "Titulo B",
            "summary": "Segundo resumen.",
            "category": "politica",
            "story_cluster_id": "story-1",
        },
        {
            "title": "Titulo B",
            "summary": "Tercera version.",
            "category": "economia",
            "story_cluster_id": "story-1",
        },
    ]

    storage_result = app._deduplicate_summaries_for_storage(summaries)
    delivery_result = app._deduplicate_summaries_for_delivery(summaries)

    assert [summary["summary"] for summary in storage_result] == [
        "Primer resumen.",
        "Tercera version.",
    ]
    assert [summary["summary"] for summary in delivery_result] == ["Primer resumen."]


@pytest.mark.asyncio
async def test_morning_delivery_respects_preferred_time():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
        schedule_timezone="America/La_Paz",
    )
    summaries = [
        {
            "title": "Titulo",
            "summary": "Resumen politico.",
            "category": "politica",
        }
    ]
    subscribers = [
        SimpleNamespace(
            channel="whatsapp",
            phone="+59170000001",
            telegram_id=None,
            categories=["politica"],
            frequency="diario",
            preferred_time="manana",
            timezone="America/La_Paz",
        ),
        SimpleNamespace(
            channel="whatsapp",
            phone="+59170000002",
            telegram_id=None,
            categories=["politica"],
            frequency="diario",
            preferred_time="noche",
            timezone="America/La_Paz",
        ),
    ]
    app = NewsSummarizerApp(settings)
    app.db = CachedSummaryDatabase(summaries, subscribers)
    app.whatsapp = FakeWhatsApp()
    app.telegram = FakeTelegram()
    app.email = FakeEmail()

    result = await app.send_summaries("morning")

    assert result["sent"] == 1
    assert app.whatsapp.sent == [
        (
            "+59170000001",
            "EcoBrief Bolivia - Brief del dia\n\n"
            "Noticias locales resumidas con menos ruido.\n\n"
            "1. Titulo\n"
            "   Resumen politico.\n\n"
            "---\n"
            "/preferencias | /cancelar",
        )
    ]


@pytest.mark.asyncio
async def test_weekly_frequency_only_sends_on_monday():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
        schedule_timezone="America/La_Paz",
    )
    subscriber = SimpleNamespace(
        channel="whatsapp",
        phone="+59170000001",
        telegram_id=None,
        categories=["politica"],
        frequency="semanal",
        preferred_time="manana",
        timezone="America/La_Paz",
    )
    app = NewsSummarizerApp(settings)
    app.db = CachedSummaryDatabase(
        [{"title": "Titulo", "summary": "Resumen politico.", "category": "politica"}],
        [subscriber],
    )
    app.whatsapp = FakeWhatsApp()
    app.telegram = FakeTelegram()
    app.email = FakeEmail()
    app._subscriber_local_now = lambda _subscriber: datetime(2026, 6, 9, 8, 0)

    result = await app.send_summaries("morning")

    assert result["sent"] == 0
    assert app.whatsapp.sent == []

    app._subscriber_local_now = lambda _subscriber: datetime(2026, 6, 8, 8, 0)
    result = await app.send_summaries("morning")

    assert result["sent"] == 1
    assert len(app.whatsapp.sent) == 1


@pytest.mark.asyncio
async def test_manual_delivery_ignores_frequency_and_preferred_time_for_demo():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
        schedule_timezone="America/La_Paz",
    )
    subscriber = SimpleNamespace(
        channel="whatsapp",
        phone="+59170000001",
        telegram_id=None,
        categories=["politica"],
        frequency="semanal",
        preferred_time="noche",
        timezone="America/La_Paz",
    )
    app = NewsSummarizerApp(settings)
    app.db = CachedSummaryDatabase(
        [{"title": "Titulo", "summary": "Resumen politico.", "category": "politica"}],
        [subscriber],
    )
    app.whatsapp = FakeWhatsApp()
    app.telegram = FakeTelegram()
    app.email = FakeEmail()
    app._subscriber_local_now = lambda _subscriber: datetime(2026, 6, 9, 8, 0)

    result = await app.send_summaries("manual")

    assert result["sent"] == 1
    assert len(app.whatsapp.sent) == 1


@pytest.mark.asyncio
async def test_email_delivery_sends_plain_text_brief():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
        schedule_timezone="America/La_Paz",
    )
    subscriber = SimpleNamespace(
        channel="email",
        phone=None,
        telegram_id=None,
        email="reader@example.com",
        categories=["politica"],
        frequency="diario",
        preferred_time="manana",
        timezone="America/La_Paz",
    )
    summaries = [
        {
            "title": "Titulo",
            "summary": "Resumen politico.",
            "fact": "Dato clave",
            "source": "Unitel",
            "url": "https://example.com/noticia",
            "category": "politica",
        }
    ]
    app = NewsSummarizerApp(settings)
    app.db = CachedSummaryDatabase(summaries, [subscriber])
    app.whatsapp = FakeWhatsApp()
    app.telegram = FakeTelegram()
    app.email = FakeEmail()

    result = await app.send_summaries("morning")

    assert result["sent"] == 1
    assert result["delivery_stats"]["sent_by_channel"]["email"] == 1
    email, subject, body, html_body = app.email.sent[0]
    assert email == "reader@example.com"
    assert subject == "EcoBrief Bolivia - Brief del dia"
    assert body == (
        "EcoBrief Bolivia - Brief del dia\n\n"
        "Noticias locales resumidas con menos ruido.\n\n"
        "1. Titulo\n"
        "   Resumen politico.\n"
        "   Dato: Dato clave\n"
        "   Fuente: Unitel\n"
        "   Link: https://example.com/noticia\n\n"
        "---\n"
        "Puedes cambiar tus preferencias o darte de baja desde EcoBrief Bolivia.\n"
    )
    assert 'href="https://example.com/noticia"' in html_body
    assert ">Link</a>" in html_body
    assert "background:#fafafa" in html_body
    assert "border-top:4px solid #16a34a" in html_body
    assert "Resumido IA" in html_body


@pytest.mark.asyncio
async def test_cached_delivery_does_not_collect_or_generate_news():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
        schedule_timezone="America/La_Paz",
    )
    subscriber = SimpleNamespace(
        channel="email",
        phone=None,
        telegram_id=None,
        email="reader@example.com",
        categories=["politica"],
        frequency="diario",
        preferred_time="manana",
        timezone="America/La_Paz",
    )
    summaries = [{"title": "Titulo", "summary": "Resumen politico.", "category": "politica"}]
    app = NewsSummarizerApp(settings)
    app.db = CachedSummaryDatabase(summaries, [subscriber])
    app.whatsapp = FakeWhatsApp()
    app.telegram = FakeTelegram()
    app.email = FakeEmail()

    async def collect_news(categories):
        raise AssertionError("deliver_cached_summaries must not collect news")

    app._collect_news = collect_news

    result = await app.deliver_cached_summaries("morning")

    assert result["collected"] == 0
    assert result["summaries"] == 1
    assert result["sent"] == 1
    assert result["used_cached_summaries"] is True
    assert app.email.sent[0][0] == "reader@example.com"


@pytest.mark.asyncio
async def test_summary_refresh_can_skip_delivery():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
        schedule_timezone="America/La_Paz",
    )
    subscriber = SimpleNamespace(
        channel="email",
        phone=None,
        telegram_id=None,
        email="reader@example.com",
        categories=["politica"],
        frequency="diario",
        preferred_time="manana",
        timezone="America/La_Paz",
    )
    summaries = [{"title": "Titulo", "summary": "Resumen politico.", "category": "politica"}]
    app = NewsSummarizerApp(settings)
    app.db = CachedSummaryDatabase(summaries, [subscriber])
    app.whatsapp = FakeWhatsApp()
    app.telegram = FakeTelegram()
    app.email = FakeEmail()

    result = await app.send_summaries("morning", deliver=False)

    assert result["summaries"] == 1
    assert result["sent"] == 0
    assert result["delivery_stats"]["sent_by_channel"]["email"] == 0
    assert app.email.sent == []


@pytest.mark.asyncio
async def test_afternoon_and_night_windows_match_exact_preferred_time():
    settings = SimpleNamespace(
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
        schedule_timezone="America/La_Paz",
    )
    summaries = [{"title": "Titulo", "summary": "Resumen.", "category": "politica"}]
    afternoon_subscriber = SimpleNamespace(
        channel="email",
        phone=None,
        telegram_id=None,
        email="afternoon@example.com",
        categories=["politica"],
        frequency="diario",
        preferred_time="tarde",
        timezone="America/La_Paz",
    )
    night_subscriber = SimpleNamespace(
        channel="email",
        phone=None,
        telegram_id=None,
        email="night@example.com",
        categories=["politica"],
        frequency="diario",
        preferred_time="noche",
        timezone="America/La_Paz",
    )
    app = NewsSummarizerApp(settings)
    app.db = CachedSummaryDatabase(summaries, [afternoon_subscriber, night_subscriber])
    app.whatsapp = FakeWhatsApp()
    app.telegram = FakeTelegram()
    app.email = FakeEmail()

    afternoon_result = await app.send_summaries("afternoon")

    assert afternoon_result["sent"] == 1
    assert app.email.sent[0][0] == "afternoon@example.com"

    app.email = FakeEmail()
    night_result = await app.send_summaries("night")

    assert night_result["sent"] == 1
    assert app.email.sent[0][0] == "night@example.com"
