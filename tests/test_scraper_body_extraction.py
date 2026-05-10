from datetime import datetime

import httpx
import pytest
from bs4 import BeautifulSoup

from src.collectors.scraper import NewsScraper, NewsSource


def test_news_source_loads_body_selector_from_config():
    source = NewsSource.from_dict(
        {
            "name": "Example",
            "url": "https://example.com/",
            "body_selector": ".article-body p",
        }
    )

    assert source.body_selector == ".article-body p"


def test_extract_body_content_uses_source_specific_selector():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="Example",
        url="https://example.com/",
        body_selector=".custom-body p",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <main>
              <p>Navigation text that should not be preferred.</p>
              <section class="custom-body">
                <p>Primer parrafo importante de la noticia con suficiente detalle.</p>
                <p>Segundo parrafo con mas contexto para el resumen de la noticia.</p>
              </section>
            </main>
          </body>
        </html>
        """,
        "lxml",
    )

    content = scraper._extract_body_content(soup, source)

    assert "Primer parrafo importante" in content
    assert "Segundo parrafo" in content
    assert "Navigation text" not in content


def test_extract_body_content_falls_back_to_generic_article_paragraphs():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="Example",
        url="https://example.com/",
        body_selector=".missing-selector p",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <article>
              <p>Primer parrafo generico con informacion suficiente de la noticia.</p>
              <p>Segundo parrafo generico con detalles adicionales del acontecimiento.</p>
            </article>
          </body>
        </html>
        """,
        "lxml",
    )

    content = scraper._extract_body_content(soup, source)

    assert "Primer parrafo generico" in content
    assert "Segundo parrafo generico" in content


@pytest.mark.asyncio
async def test_enrich_article_adds_content_excerpt_word_count_and_description():
    detail_html = """
    <html>
      <body>
        <article>
          <div class="body">
            <p>Este es el primer parrafo de la noticia con datos importantes.</p>
            <p>Este es el segundo parrafo de la noticia con contexto adicional.</p>
          </div>
          <img src="/image.jpg" />
        </article>
      </body>
    </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.com/news/1"
        return httpx.Response(200, text=detail_html)

    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="Example",
        url="https://example.com/",
        body_selector=".body p",
    )
    article = {
        "title": "Titulo de prueba",
        "url": "https://example.com/news/1",
        "source": "Example",
        "published_at": datetime.now(),
        "description": "",
        "image": None,
    }

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        enriched = await scraper._enrich_article(client, article, source)

    assert "primer parrafo" in enriched["content"]
    assert enriched["excerpt"].startswith("Este es el primer parrafo")
    assert enriched["description"] == enriched["excerpt"]
    assert enriched["content_word_count"] > 10
    assert enriched["content_collected_at"] is not None
    assert enriched["image"] == "https://example.com/image.jpg"
