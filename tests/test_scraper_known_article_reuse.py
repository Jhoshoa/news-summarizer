"""Tests for skipping the detail-page re-fetch when we already have content
for a URL and it's old enough to assume it's not still changing.

Every pipeline run used to re-fetch the full article page for every listing
item regardless of whether it had already been scraped minutes/hours
earlier that same day -- confirmed live: a day with 9 runs re-requested the
same ~200 article pages up to 9 times each. This only skips the detail
fetch when the article is old enough (SCRAPER_DETAIL_REFRESH_HOURS, default
3h) that it's unlikely to still be updating; fresh/developing coverage
keeps getting re-checked every run like before.
"""

from datetime import datetime, timedelta

import httpx
import pytest

from src.collectors.scraper import NewsScraper, NewsSource


def _known(*, content="Contenido ya guardado con suficiente detalle.", published_at=None, description=None, image=None):
    return {
        "content": content,
        "description": description,
        "image": image,
        "published_at": published_at,
    }


def test_can_reuse_known_article_when_old_enough():
    scraper = NewsScraper(sources=[], detail_refresh_hours=3)
    old_enough = scraper._now() - timedelta(hours=4)

    assert scraper._can_reuse_known_article(_known(published_at=old_enough)) is True


def test_cannot_reuse_known_article_when_too_recent():
    scraper = NewsScraper(sources=[], detail_refresh_hours=3)
    too_recent = scraper._now() - timedelta(hours=1)

    assert scraper._can_reuse_known_article(_known(published_at=too_recent)) is False


def test_cannot_reuse_known_article_without_content():
    scraper = NewsScraper(sources=[], detail_refresh_hours=3)
    old_enough = scraper._now() - timedelta(hours=10)

    assert scraper._can_reuse_known_article(_known(content=None, published_at=old_enough)) is False


def test_cannot_reuse_known_article_without_published_at():
    scraper = NewsScraper(sources=[], detail_refresh_hours=3)

    assert scraper._can_reuse_known_article(_known(published_at=None)) is False


def test_apply_known_article_fills_fields_without_overwriting_listing_data():
    scraper = NewsScraper(sources=[], detail_refresh_hours=3)
    published_at = scraper._now() - timedelta(hours=5)
    known = _known(
        content="Contenido completo guardado de una corrida anterior.",
        description="Descripcion guardada.",
        image="https://example.com/foto.jpg",
        published_at=published_at,
    )
    article = {
        "title": "Titulo del listado",
        "url": "https://example.com/nota",
        "description": "",  # vacio en el listado, se debe completar
        "image": None,
    }

    result = scraper._apply_known_article(article, known)

    assert result["content"] == known["content"]
    assert result["description"] == "Descripcion guardada."
    assert result["image"] == "https://example.com/foto.jpg"
    assert result["published_at"] == published_at
    assert result["published_at_from_detail"] is True
    assert result["detail_reused"] is True
    # No pisa un description que el listado ya traia.
    article2 = {"title": "T", "url": "u", "description": "Del listado", "image": "listado.jpg"}
    result2 = scraper._apply_known_article(article2, known)
    assert result2["description"] == "Del listado"
    assert result2["image"] == "listado.jpg"


@pytest.mark.asyncio
async def test_enrich_article_skips_http_fetch_when_reusable():
    scraper = NewsScraper(sources=[], detail_refresh_hours=3)
    source = NewsSource(name="Example", url="https://example.com/")
    old_enough = scraper._now() - timedelta(hours=6)

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, text="<html></html>")

    article = {
        "title": "Nota ya scrapeada",
        "url": "https://example.com/nota-vieja",
        "hash": "abc123",
        "description": "",
        "image": None,
    }
    known_articles = {
        "abc123": _known(
            content="Contenido guardado hace horas, ya no deberia cambiar.",
            published_at=old_enough,
        )
    }

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await scraper._enrich_article(client, article, source, known_articles)

    assert calls == []  # no se hizo ningun request HTTP
    assert result["detail_reused"] is True
    assert result["content"] == known_articles["abc123"]["content"]


@pytest.mark.asyncio
async def test_enrich_article_still_fetches_when_known_article_is_too_recent():
    scraper = NewsScraper(sources=[], detail_refresh_hours=3)
    source = NewsSource(name="Example", url="https://example.com/", body_selector=".body p")
    too_recent = scraper._now() - timedelta(minutes=30)

    detail_html = """
    <html><body><article class="body">
      <p>Contenido fresco bajado en esta corrida con suficiente detalle para pasar el filtro.</p>
    </article></body></html>
    """

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, text=detail_html)

    article = {
        "title": "Nota en desarrollo",
        "url": "https://example.com/nota-fresca",
        "hash": "def456",
        "description": "",
        "image": None,
    }
    known_articles = {
        "def456": _known(content="Version vieja de hace 30 minutos.", published_at=too_recent)
    }

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await scraper._enrich_article(client, article, source, known_articles)

    assert calls == ["https://example.com/nota-fresca"]  # si se volvio a pedir
    assert not result.get("detail_reused")
    assert "Contenido fresco" in result["content"]


@pytest.mark.asyncio
async def test_enrich_article_fetches_normally_without_known_articles():
    """El comportamiento sin known_articles (o vacio) no cambia -- llamadas
    existentes que no pasan el parametro siguen funcionando igual."""

    scraper = NewsScraper(sources=[], detail_refresh_hours=3)
    source = NewsSource(name="Example", url="https://example.com/", body_selector=".body p")
    detail_html = """
    <html><body><article class="body">
      <p>Contenido normal de un articulo nuevo con suficiente texto de prueba.</p>
    </article></body></html>
    """

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, text=detail_html)

    article = {"title": "Nota nueva", "url": "https://example.com/nota-nueva", "hash": "xyz789"}

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await scraper._enrich_article(client, article, source)

    assert calls == ["https://example.com/nota-nueva"]
    assert "Contenido normal" in result["content"]
