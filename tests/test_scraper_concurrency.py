"""Tests for bounded concurrency in the scraper.

Every source used to be scraped one at a time, and within a source every
detail page was fetched one at a time too -- confirmed live this took
several minutes per run. SCRAPER_CONCURRENCY existed as a setting but was
never actually connected to anything (a dead config), which is exactly the
kind of regression these tests guard against: not just "does concurrency
work", but "does the concurrency limit from settings actually reach the
scraper, and does it actually cap how many requests are in flight at once".

Two separate limits, matching two separate risks:
- `concurrency` (fetch_all): how many of the ~6 sources run at once. Safe to
  raise since each source is an independent site with no shared quota.
- `detail_concurrency` (_enrich_articles): how many detail-page requests hit
  the SAME source at once. Kept smaller/separate on purpose -- hammering one
  site with dozens of simultaneous requests looks like abusive traffic even
  if the other sources are untouched.
"""

import asyncio

import httpx
import pytest

from src.collectors.scraper import NewsScraper, NewsSource


def _source(name: str) -> NewsSource:
    return NewsSource(name=name, url=f"https://example.com/{name.lower()}/")


def _article(idx: int) -> dict:
    return {"title": f"Articulo {idx}", "url": f"https://example.com/a{idx}", "hash": f"hash{idx}"}


# --- constructor defaults / wiring -----------------------------------------


def test_default_concurrency_values():
    scraper = NewsScraper(sources=[])
    assert scraper.concurrency == 3
    assert scraper.detail_concurrency == 5


def test_custom_concurrency_values_are_respected():
    scraper = NewsScraper(sources=[], concurrency=7, detail_concurrency=2)
    assert scraper.concurrency == 7
    assert scraper.detail_concurrency == 2


def test_concurrency_is_clamped_to_at_least_one():
    scraper = NewsScraper(sources=[], concurrency=0, detail_concurrency=-5)
    assert scraper.concurrency == 1
    assert scraper.detail_concurrency == 1


# --- fetch_all: cross-source concurrency ------------------------------------


@pytest.mark.asyncio
async def test_fetch_all_never_exceeds_the_source_concurrency_limit(monkeypatch):
    scraper = NewsScraper(sources=[], concurrency=2, detail_concurrency=5)
    scraper.sources = [_source(f"Source{i}") for i in range(6)]

    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    async def fake_scrape_source(client, source, known_articles):
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        async with lock:
            in_flight -= 1
        return [dict(_article(0), title=source.name)], 0

    monkeypatch.setattr(scraper, "_scrape_source", fake_scrape_source)

    await scraper.fetch_all()

    assert max_in_flight <= 2
    # confirma que de verdad hubo solapamiento (no quedo serializado por accidente)
    assert max_in_flight >= 2


@pytest.mark.asyncio
async def test_fetch_all_preserves_source_order_regardless_of_completion_order(monkeypatch):
    scraper = NewsScraper(sources=[], concurrency=3)
    scraper.sources = [_source("Slow"), _source("Fast1"), _source("Fast2")]

    async def fake_scrape_source(client, source, known_articles):
        # la primera fuente es la mas lenta -- si el orden dependiera de
        # cuando termina cada una, "Slow" quedaria al final del resultado
        delay = 0.05 if source.name == "Slow" else 0.01
        await asyncio.sleep(delay)
        return [dict(_article(0), title=source.name, hash=source.name)], 0

    monkeypatch.setattr(scraper, "_scrape_source", fake_scrape_source)

    results = await scraper.fetch_all()

    assert [a["title"] for a in results] == ["Slow", "Fast1", "Fast2"]


@pytest.mark.asyncio
async def test_fetch_all_isolates_one_source_failing_from_the_rest(monkeypatch):
    scraper = NewsScraper(sources=[], concurrency=3)
    scraper.sources = [_source("Good1"), _source("Bad"), _source("Good2")]

    async def fake_scrape_source(client, source, known_articles):
        if source.name == "Bad":
            raise RuntimeError("fuente caida")
        return [dict(_article(0), title=source.name, hash=source.name)], 0

    monkeypatch.setattr(scraper, "_scrape_source", fake_scrape_source)

    results = await scraper.fetch_all()

    assert {a["title"] for a in results} == {"Good1", "Good2"}


# --- _enrich_articles: per-source detail-page concurrency -------------------


@pytest.mark.asyncio
async def test_enrich_articles_never_exceeds_the_detail_concurrency_limit(monkeypatch):
    scraper = NewsScraper(sources=[], detail_concurrency=3)
    source = _source("Test")
    articles = [_article(i) for i in range(10)]

    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    async def fake_enrich_article(client, article, src, known_articles):
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.03)
        async with lock:
            in_flight -= 1
        return article

    monkeypatch.setattr(scraper, "_enrich_article", fake_enrich_article)

    async with httpx.AsyncClient() as client:
        await scraper._enrich_articles(client, articles, source)

    assert max_in_flight <= 3
    assert max_in_flight >= 2


@pytest.mark.asyncio
async def test_enrich_articles_preserves_order_regardless_of_completion_order(monkeypatch):
    scraper = NewsScraper(sources=[], detail_concurrency=5)
    source = _source("Test")
    articles = [_article(i) for i in range(5)]

    async def fake_enrich_article(client, article, src, known_articles):
        delay = 0.05 if article["title"] == "Articulo 0" else 0.01
        await asyncio.sleep(delay)
        return article

    monkeypatch.setattr(scraper, "_enrich_article", fake_enrich_article)

    async with httpx.AsyncClient() as client:
        result = await scraper._enrich_articles(client, articles, source)

    assert [a["title"] for a in result] == [f"Articulo {i}" for i in range(5)]


@pytest.mark.asyncio
async def test_enrich_articles_isolates_one_article_failing_from_the_rest(monkeypatch):
    scraper = NewsScraper(sources=[], detail_concurrency=3)
    source = _source("Test")
    articles = [_article(0), _article(1), _article(2)]

    async def fake_enrich_article(client, article, src, known_articles):
        if article["title"] == "Articulo 1":
            raise RuntimeError("timeout de red")
        return {**article, "content": "contenido"}

    monkeypatch.setattr(scraper, "_enrich_article", fake_enrich_article)

    async with httpx.AsyncClient() as client:
        result = await scraper._enrich_articles(client, articles, source)

    # el que fallo vuelve tal cual (sin "content"), como hacia el loop
    # secuencial de antes -- no tumba a los otros dos.
    assert result[0]["content"] == "contenido"
    assert "content" not in result[1]
    assert result[2]["content"] == "contenido"


# --- real concurrency end-to-end with an actual (mocked) HTTP client -------


@pytest.mark.asyncio
async def test_enrich_articles_actually_overlaps_real_http_requests():
    """A diferencia de los tests de arriba (que reemplazan _enrich_article),
    este ejercita el camino real completo -- MockTransport con una demora
    real -- para confirmar que el solapamiento tambien pasa a nivel HTTP,
    no solo a nivel de la funcion que orquesta las tareas."""

    scraper = NewsScraper(sources=[], detail_concurrency=4)
    source = NewsSource(name="Test", url="https://example.com/", body_selector=".body p")
    articles = [
        {"title": f"Articulo {i}", "url": f"https://example.com/a{i}", "hash": f"hash{i}"}
        for i in range(8)
    ]

    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()
    detail_html = (
        "<html><body><article class='body'>"
        "<p>Contenido de prueba con suficiente longitud para pasar el filtro de calidad.</p>"
        "</article></body></html>"
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.03)
        async with lock:
            in_flight -= 1
        return httpx.Response(200, text=detail_html)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await scraper._enrich_articles(client, articles, source)

    assert len(result) == 8
    assert max_in_flight <= 4
    assert max_in_flight >= 2


# --- settings -> NewsScraper wiring (regression guard) ----------------------


@pytest.mark.asyncio
async def test_collect_news_passes_concurrency_settings_to_the_scraper(monkeypatch):
    """Regression test: SCRAPER_CONCURRENCY used to be defined in settings.py
    but never actually reached NewsScraper -- scraping stayed fully
    sequential no matter what the setting said. This asserts the wiring
    itself, not just that the scraper's own concurrency logic works."""

    import src.main as main_module
    from src.config.settings import Settings

    captured_kwargs: dict = {}

    class FakeScraper:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        async def fetch_all(self, categories=None, known_articles=None):
            return []

    monkeypatch.setattr(main_module, "NewsScraper", FakeScraper)
    monkeypatch.setenv("SCRAPER_CONCURRENCY", "9")
    monkeypatch.setenv("SCRAPER_DETAIL_CONCURRENCY", "4")

    settings = Settings(_env_file=None)
    app = main_module.NewsSummarizerApp(settings)

    await app._collect_news(["general"])

    assert captured_kwargs.get("concurrency") == 9
    assert captured_kwargs.get("detail_concurrency") == 4
