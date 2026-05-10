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


def test_extract_body_content_uses_json_ld_article_body_before_css():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="Example",
        url="https://example.com/",
        body_selector=".missing-selector p",
    )
    soup = BeautifulSoup(
        """
        <html>
          <head>
            <script type="application/ld+json">
              {
                "@type": "NewsArticle",
                "articleBody": "Primer parrafo desde JSON-LD con detalles suficientes. Segundo parrafo desde JSON-LD con contexto adicional para resumen."
              }
            </script>
          </head>
          <body><main><p>Texto corto.</p></main></body>
        </html>
        """,
        "lxml",
    )

    content = scraper._extract_body_content(soup, source)

    assert "Primer parrafo desde JSON-LD" in content
    assert "Segundo parrafo desde JSON-LD" in content


def test_extract_body_content_uses_readable_text_fallback_after_title():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="Unitel",
        url="https://unitel.bo/",
        body_selector=".missing-selector p",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <nav>Inicio Politica Seguridad Economia</nav>
            <h1>"Utilizan un taladro para colocar fierros sobre la via": Ministro denuncia danos en la ruta La Paz - Oruro</h1>
            <h2>El ministro presento un video en el que se ve a una persona que utiliza un taladro para danar el asfalto.</h2>
            <span>Publicacion: Hace 28 minutos</span>
            <span>Unitel Digital</span>
            <div>El ministro de Obras Publicas denuncio este domingo que personas fueron captadas ocasionando danos a la carretera.</div>
            <div>Segun la autoridad, transportistas enviaron imagenes donde se observa a una persona utilizando un taladro para perforar el asfalto.</div>
            <div>MIRA AQUI: Otra noticia relacionada</div>
            <div>Recibe las noticias de ultimo momento en tu email</div>
            <div>Este texto de newsletter no debe aparecer.</div>
          </body>
        </html>
        """,
        "lxml",
    )

    content = scraper._extract_body_content(soup, source)

    assert "El ministro de Obras Publicas denuncio" in content
    assert "transportistas enviaron imagenes" in content
    assert "newsletter" not in content


def test_extract_image_ignores_logo_urls():
    scraper = NewsScraper(sources=[])
    source = NewsSource(name="Unitel", url="https://unitel.bo/")
    soup = BeautifulSoup(
        '<html><body><img src="https://cdn2.unitel.bo/unitel/v2-resources/vu/img/logo-unitel.png" /></body></html>',
        "lxml",
    )

    assert scraper._extract_image(soup, source) is None


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
