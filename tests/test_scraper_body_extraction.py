from datetime import datetime, timedelta

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
                <p>Segundo parrafo con mas contexto para el resumen de la noticia y datos adicionales relevantes para superar el minimo.</p>
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
              <p>Segundo parrafo generico con detalles adicionales del acontecimiento y contexto suficiente para validar el contenido extraido.</p>
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


def test_extract_body_content_ignores_json_ld_description_as_body():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="Example",
        url="https://example.com/",
        body_selector=".article-body p",
    )
    soup = BeautifulSoup(
        """
        <html>
          <head>
            <script type="application/ld+json">
              {
                "@type": "NewsArticle",
                "description": "Entradilla breve que no es el cuerpo completo."
              }
            </script>
          </head>
          <body>
            <article class="article-body">
              <p>Primer parrafo real de la noticia con informacion suficiente para superar el minimo.</p>
              <p>Segundo parrafo real con contexto adicional y datos importantes del acontecimiento.</p>
            </article>
          </body>
        </html>
        """,
        "lxml",
    )

    content = scraper._extract_body_content(soup, source)

    assert "Entradilla breve" not in content
    assert "Primer parrafo real" in content
    assert "Segundo parrafo real" in content


def test_clean_text_decodes_entities_tags_spacing_and_mojibake():
    scraper = NewsScraper(sources=[])

    content = scraper._clean_text(
        "El pa&iacute;s anunci&oacute; &lt;b&gt;nuevas medidas&lt;/b&gt; "
        "para la ni&#241;ez y la educaci&#xF3;n.&nbsp;&amp;oacute; "
        "La pol\u00c3\u00adtica incluy\u00c3\u00b3 "
        "\u00e2\u20ac\u0153di\u00c3\u00a1logo\u00e2\u20ac\u009d.\u200b"
    )

    assert content == (
        'El país anunció nuevas medidas para la niñez y la educación. ó '
        'La política incluyó "diálogo".'
    )
    assert "&" not in content
    assert "<b>" not in content
    assert "\u200b" not in content


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


@pytest.mark.asyncio
async def test_unitel_listing_date_skips_non_today_detail_fetch():
    scraper = NewsScraper(sources=[])
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    source = NewsSource(
        name="Unitel",
        url="https://unitel.bo/",
        selector="article",
        title_selector="h2 a",
        url_selector="h2 a",
        date_selector=".vu-td-fdp, .fecha, .date, time",
        body_selector="main article p",
    )
    requested_urls = []

    listing_html = f"""
        <html>
          <body>
            <article>
              <span class="vu-td-fdp">Publicacion: {today:%d/%m/%Y %H:%M}</span>
              <h2><a href="/noticias/hoy">Noticia actual de Unitel con fecha de hoy</a></h2>
            </article>
            <article>
              <span class="vu-td-fdp">Publicacion: {yesterday:%d/%m/%Y %H:%M}</span>
              <h2><a href="/noticias/ayer">Noticia antigua de Unitel con fecha de ayer</a></h2>
            </article>
          </body>
        </html>
    """
    detail_html = f"""
        <html>
          <body>
            <span class="vu-td-fdp">Publicacion: {today:%d/%m/%Y %H:%M}</span>
            <main>
              <article>
                <p>Contenido suficiente para una noticia real de Unitel recolectada hoy.</p>
                <p>Segundo parrafo con contexto adicional para superar validaciones del scraper.</p>
              </article>
            </main>
          </body>
        </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if str(request.url) == "https://unitel.bo/":
            return httpx.Response(200, text=listing_html)
        return httpx.Response(200, text=detail_html)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    ) as client:
        articles = await scraper._scrape_source(client, source)

    assert [article["title"] for article in articles] == [
        "Noticia actual de Unitel con fecha de hoy"
    ]
    assert "https://unitel.bo/noticias/hoy" in requested_urls
    assert "https://unitel.bo/noticias/ayer" not in requested_urls


def test_reduno_fallback_skips_related_blocks_but_keeps_later_body():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RedUno",
        url="https://www.reduno.com.bo/",
        body_selector=".missing-selector p",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <h1>Paz dice que no se puede aceptar la violencia en las protestas sindicales en Bolivia</h1>
            <p>En una declaracion a los medios en La Paz, el gobernante lamento el acto violento ocurrido el miercoles.</p>
            <span>EFE</span>
            <span>08/05/2026 7:57</span>
            <div>La Paz, Bolivia</div>
            <div>Escuchar esta nota</div>
            <div>El presidente sostuvo este jueves que no se puede aceptar la violencia en las protestas sindicales.</div>
            <div>Te puede interesar:</div>
            <a>Multisectores se suman en rechazo a la posible abrogacion de Ley 1720</a>
            <div>Los manifestantes defendieron su accion como una toma simbolica del edificio por varias horas.</div>
            <div>Comentarios</div>
            <div>Mas leidas</div>
          </body>
        </html>
        """,
        "lxml",
    )

    content = scraper._extract_body_content(soup, source)

    assert "El presidente sostuvo este jueves" in content
    assert "Los manifestantes defendieron" in content
    assert "Multisectores se suman" not in content
    assert "Mas leidas" not in content


def test_reduno_current_detail_markup_uses_body_cuerpo_paragraphs():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RedUno",
        url="https://www.reduno.com.bo/",
        body_selector=".body__cuerpo p, .contenedor.body p",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <h1>Las frases que dejo Paz al promulgar Ley de Estados de Excepcion</h1>
            <p>Entradilla que pertenece a la cabecera y no debe entrar como cuerpo.</p>
            <div class="body__cuerpo">
              <p class="texto-justify">El presidente del Estado promulgo este lunes la Ley de Regulacion de los Estados de Excepcion con procedimientos y alcances definidos.</p>
              <p class="texto-justify blockquote">Durante el acto de promulgacion, el mandatario dejo una serie de frases sobre seguridad y economia.</p>
              <div class="link_nota_propia">
                <div class="nota__relacionada">Te puede interesar:</div>
                <div class="titulo"><a>Paz promulga la Ley que regula los Estados de Excepcion en Bolivia</a></div>
              </div>
              <p class="texto-justify">Paz advirtio que el principal riesgo para el pais es la inseguridad vinculada a grupos criminales.</p>
            </div>
          </body>
        </html>
        """,
        "lxml",
    )

    content = scraper._extract_body_content(soup, source)

    assert "El presidente del Estado promulgo" in content
    assert "Durante el acto de promulgacion" in content
    assert "Paz advirtio que el principal riesgo" in content
    assert "Entradilla que pertenece" not in content
    assert "Te puede interesar" not in content
    assert "Paz promulga la Ley que regula" not in content


@pytest.mark.asyncio
async def test_enrich_article_prefers_meta_description_over_generated_excerpt():
    detail_html = """
        <html>
          <head>
            <meta property="og:description" content="Entradilla real de RedUno con contexto de la noticia." />
          </head>
          <body>
            <div class="body__cuerpo">
              <p>Primer parrafo completo de la noticia con informacion suficiente para el lector y detalles centrales del hecho investigado por las autoridades.</p>
              <p>Segundo parrafo completo con mas contexto y detalles importantes del acontecimiento para superar el minimo de palabras del extractor.</p>
            </div>
          </body>
        </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=detail_html)

    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RedUno",
        url="https://www.reduno.com.bo/",
        body_selector=".body__cuerpo p",
    )
    article = {
        "title": "Titulo de prueba",
        "url": "https://www.reduno.com.bo/noticias/test",
        "source": "RedUno",
        "published_at": datetime.now(),
        "description": "",
        "image": None,
    }

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        enriched = await scraper._enrich_article(client, article, source)

    assert enriched["description"] == "Entradilla real de RedUno con contexto de la noticia."
    assert "Primer parrafo completo" in enriched["content"]


def test_reduno_listing_extracts_current_article_card_markup():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RedUno",
        url="https://www.reduno.com.bo/noticias/nacionales",
        selector="article.nota, article.nota_gen, article.nota--general",
        title_selector="div.titulo a, h2 a, h2",
        url_selector="div.titulo a",
        date_selector="input.nota_fecha_input",
        date_attr="data-fecha-a",
        image_selector="figure.nota__media img",
    )
    soup = BeautifulSoup(
        """
        <article class="nota nota--general nota_gen">
          <div class="volanta"><a>Nacionales</a></div>
          <figure class="nota__media">
            <img src="/uploads/reduno.jpg" />
          </figure>
          <div class="titulo">
            <a href="/noticias/magisterio-ratifica-paro-2026510124459">
              Magisterio Urbano y Rural ratifican el paro de 24 y 48 horas
            </a>
          </div>
          <input class="nota_fecha_input" data-fecha-a="10/05/2026 12:44" />
        </article>
        """,
        "lxml",
    )

    article = scraper._extract_article(soup.select_one("article"), source)

    assert article["source"] == "RedUno"
    assert article["title"] == "Magisterio Urbano y Rural ratifican el paro de 24 y 48 horas"
    assert article["url"] == (
        "https://www.reduno.com.bo/noticias/magisterio-ratifica-paro-2026510124459"
    )
    assert article["image"] == "https://www.reduno.com.bo/uploads/reduno.jpg"
    assert article["published_at"] == datetime(2026, 5, 10, 12, 44)


def test_reduno_date_parser_uses_bolivian_day_first_format():
    scraper = NewsScraper(sources=[])

    parsed = scraper._parse_date("09/06/2026 8:57")

    assert parsed == datetime(2026, 6, 9, 8, 57)


def test_reduno_date_parser_accepts_millisecond_timestamp():
    scraper = NewsScraper(sources=[])

    parsed = scraper._parse_date("1781143220992")

    assert parsed == datetime(2026, 6, 10, 22, 0, 20, 992000)


def test_spanish_month_date_parser_does_not_shift_month_and_day():
    scraper = NewsScraper(sources=[])

    parsed = scraper._parse_date("10 de junio de 2026 11:20")

    assert parsed == datetime(2026, 6, 10, 11, 20)


def test_redbolivision_date_parser_accepts_meta_date_format():
    scraper = NewsScraper(sources=[])

    parsed = scraper._parse_date("10 de Junio de 2026 - 23:09")

    assert parsed == datetime(2026, 6, 10, 23, 9)


def test_lostiempos_date_parser_accepts_date_publish_format():
    scraper = NewsScraper(sources=[])

    parsed = scraper._parse_date("Publicado el 10/06/2026 a las 23h46")

    assert parsed == datetime(2026, 6, 10, 23, 46)


def test_eldeber_date_parser_accepts_article_date_format():
    scraper = NewsScraper(sources=[])

    parsed = scraper._parse_date("Miércoles, 10 de junio de 2026 a las 12:57")

    assert parsed == datetime(2026, 6, 10, 12, 57)


def test_spanish_month_first_date_parser_does_not_shift_month_and_day():
    scraper = NewsScraper(sources=[])

    parsed = scraper._parse_date("junio 10, 2026 11:20")

    assert parsed == datetime(2026, 6, 10, 11, 20)


def test_filter_usable_articles_drops_future_publish_dates():
    scraper = NewsScraper(sources=[])
    source = NewsSource(name="RadioFides", url="https://www.radiofides.com/")
    articles = [
        {
            "title": "Noticia con fecha futura",
            "content": "Contenido suficiente para que el articulo sea usable dentro del pipeline.",
            "published_at": datetime.now() + timedelta(days=10),
        },
        {
            "title": "Noticia valida",
            "content": "Contenido suficiente para que el articulo sea usable dentro del pipeline.",
            "published_at": datetime.now(),
        },
    ]

    filtered = scraper._filter_usable_articles(articles, source)

    assert [article["title"] for article in filtered] == ["Noticia valida"]


@pytest.mark.asyncio
async def test_reduno_detail_date_replaces_fallback_listing_date():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RedUno",
        url="https://www.reduno.com.bo/noticias/nacionales",
        date_selector="input.nota_fecha_input, .autor-fecha .fecha, .autor .fecha, .fecha",
        date_attr="data-fecha-a",
    )

    class FakeClient:
        async def get(self, url):
            class Response:
                text = """
                <html>
                  <head>
                    <meta property="og:description" content="Descripcion de prueba." />
                  </head>
                  <body>
                    <div class="autor-fecha">
                      <div class="autor">Red Uno Digital</div>
                      <p class="fecha">09/06/2026 8:57</p>
                    </div>
                    <main><article><p>Contenido suficientemente largo para una noticia real de prueba.</p></article></main>
                  </body>
                </html>
                """

                def raise_for_status(self):
                    return None

            return Response()

    article = {
        "title": "Persisten los puntos de bloqueo que afectan el abastecimiento",
        "url": "https://www.reduno.com.bo/noticias/mapa-de-transitabilidad",
        "published_at": datetime(2026, 6, 11, 0, 26),
    }

    enriched = await scraper._enrich_article(FakeClient(), article, source)

    assert enriched["published_at"] == datetime(2026, 6, 9, 8, 57)


@pytest.mark.asyncio
async def test_unitel_detail_date_replaces_fallback_listing_date():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="Unitel",
        url="https://unitel.bo/",
        date_selector=".fecha, .date, time",
    )

    class FakeClient:
        async def get(self, url):
            class Response:
                text = """
                <html>
                  <head>
                    <meta property="og:description" content="Descripcion de Unitel." />
                  </head>
                  <body>
                    <time datetime="2026-06-10T14:36:46">10/06/2026 14:36</time>
                    <main><article><p>Contenido suficientemente largo para una noticia real de prueba.</p></article></main>
                  </body>
                </html>
                """

                def raise_for_status(self):
                    return None

            return Response()

    article = {
        "title": "Policia de Cochabamba aclara operativo",
        "url": "https://unitel.bo/noticias/seguridad/example",
        "published_at": datetime(2026, 6, 11, 0, 26),
    }

    enriched = await scraper._enrich_article(FakeClient(), article, source)

    assert enriched["published_at"] == datetime(2026, 6, 10, 14, 36)


def test_detail_date_extracts_generic_article_published_time_meta():
    scraper = NewsScraper(sources=[])
    source = NewsSource(name="Generic", url="https://example.com/")
    soup = BeautifulSoup(
        """
        <html>
          <head>
            <meta property="article:published_time" content="2026-06-08T09:15:00" />
          </head>
        </html>
        """,
        "lxml",
    )

    assert scraper._extract_detail_date(soup, source) == datetime(2026, 6, 8, 9, 15)


def test_unitel_detail_date_extracts_specific_publication_class():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="Unitel",
        url="https://unitel.bo/",
        date_selector=".UNITEL_DETALLE_FECHA_PUBLICACION, .fecha, .date, time",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <span class="UNITEL_DETALLE_FECHA_PUBLICACION">
              Publicado el: 10/06/2026 08:42
            </span>
          </body>
        </html>
        """,
        "lxml",
    )

    assert scraper._extract_detail_date(soup, source) == datetime(2026, 6, 10, 8, 42)


def test_filter_usable_articles_drops_non_today_detail_date_even_with_description():
    scraper = NewsScraper(sources=[])
    source = NewsSource(name="Unitel", url="https://unitel.bo/")

    articles = scraper._filter_usable_articles(
        [
            {
                "title": "Noticia antigua con descripcion suficiente",
                "description": "Descripcion suficientemente larga para pasar la validacion de texto util.",
                "published_at": datetime.now() - timedelta(days=1),
                "skipped_detail_reason": "non_today_detail_date",
            },
            {
                "title": "Noticia actual con descripcion suficiente",
                "description": "Descripcion suficientemente larga para pasar la validacion de texto util.",
                "published_at": datetime.now(),
            },
        ],
        source,
    )

    assert [article["title"] for article in articles] == [
        "Noticia actual con descripcion suficiente"
    ]


def test_unitel_extracts_public_main_image_from_data_srcset():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="Unitel",
        url="https://unitel.bo/",
        image_selector="div[frame='imagenPrincipalNota_B'] img, meta[property='og:image'], img",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <div frame="imagenPrincipalNota_B">
              <img
                src="//estaticos.unitel.bo/placeholder/svg/viewbox/1024x512"
                data-srcset="//estaticos.unitel.bo/binrepository/1024x545/0c17/1024d512/none/246276540/HAKB/unitel-noticias_101-15749089_20260611012545.jpg 1024w,//estaticos.unitel.bo/binrepository/512x273/0c9/512d256/none/246276540/XUJI/unitel-noticias_101-15749089_20260611012545.jpg 512w"
              />
            </div>
          </body>
        </html>
        """,
        "lxml",
    )

    assert scraper._extract_image(soup, source) == (
        "https://estaticos.unitel.bo/binrepository/1024x545/0c17/1024d512/none/"
        "246276540/HAKB/unitel-noticias_101-15749089_20260611012545.jpg"
    )


def test_redbolivision_detail_date_extracts_single_layout_meta_date():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RedBolivision",
        url="https://www.redbolivision.tv.bo/",
        date_selector=".single-layout__meta-date, .fecha, time",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <span class="single-layout__meta-date">10 de Junio de 2026 - 23:09</span>
          </body>
        </html>
        """,
        "lxml",
    )

    assert scraper._extract_detail_date(soup, source) == datetime(2026, 6, 10, 23, 9)


def test_lostiempos_extracts_listing_date_from_url():
    scraper = NewsScraper(sources=[])

    parsed = scraper._extract_date_from_url(
        "https://www.lostiempos.com/actualidad/pais/20260610/denuncian-presiones"
    )

    assert parsed == datetime(2026, 6, 10)


def test_eldeber_extracts_listing_date_from_compact_url_suffix():
    scraper = NewsScraper(sources=[])

    parsed = scraper._extract_date_from_url(
        "https://eldeber.com.bo/bbc/hallazgo-en-el-indico-2026610214845"
    )

    assert parsed == datetime(2026, 6, 10, 21, 48, 45)


def test_lostiempos_detail_date_extracts_date_publish_text():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="LosTiempos",
        url="https://www.lostiempos.com/actualidad",
        date_selector=".date-publish, time",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <div class="date-publish">Publicado el 10/06/2026 a las 23h46</div>
          </body>
        </html>
        """,
        "lxml",
    )

    assert scraper._extract_detail_date(soup, source) == datetime(2026, 6, 10, 23, 46)


def test_eldeber_detail_date_extracts_articulo_fecha_text():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="ElDeber",
        url="https://eldeber.com.bo/ultimas-noticias",
        date_selector=".articulo__fecha, time",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <div class="articulo__fecha">Miércoles, 10 de junio de 2026 a las 12:57</div>
          </body>
        </html>
        """,
        "lxml",
    )

    assert scraper._extract_detail_date(soup, source) == datetime(2026, 6, 10, 12, 57)


@pytest.mark.asyncio
async def test_lostiempos_url_date_skips_non_today_detail_fetch():
    scraper = NewsScraper(sources=[])
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    source = NewsSource(
        name="LosTiempos",
        url="https://www.lostiempos.com/actualidad",
        selector=".views-row",
        title_selector=".views-field-title a",
        url_selector=".views-field-title a",
        date_selector=".date-publish, time",
        body_selector="article p",
    )
    requested_urls = []

    listing_html = f"""
        <html>
          <body>
            <div class="views-row">
              <div class="views-field-title">
                <a href="/actualidad/pais/{today:%Y%m%d}/noticia-hoy">
                  Noticia actual de Los Tiempos con fecha de hoy
                </a>
              </div>
            </div>
            <div class="views-row">
              <div class="views-field-title">
                <a href="/actualidad/pais/{yesterday:%Y%m%d}/noticia-ayer">
                  Noticia antigua de Los Tiempos con fecha de ayer
                </a>
              </div>
            </div>
          </body>
        </html>
    """
    detail_html = f"""
        <html>
          <body>
            <div class="date-publish">Publicado el {today:%d/%m/%Y} a las 23h46</div>
            <article>
              <p>Contenido suficiente para una noticia real de Los Tiempos recolectada hoy.</p>
              <p>Segundo parrafo con contexto adicional para superar validaciones del scraper.</p>
            </article>
          </body>
        </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if str(request.url) == "https://www.lostiempos.com/actualidad":
            return httpx.Response(200, text=listing_html)
        return httpx.Response(200, text=detail_html)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    ) as client:
        articles = await scraper._scrape_source(client, source)

    assert [article["title"] for article in articles] == [
        "Noticia actual de Los Tiempos con fecha de hoy"
    ]
    assert f"https://www.lostiempos.com/actualidad/pais/{today:%Y%m%d}/noticia-hoy" in (
        requested_urls
    )
    assert f"https://www.lostiempos.com/actualidad/pais/{yesterday:%Y%m%d}/noticia-ayer" not in (
        requested_urls
    )


def test_reduno_link_fallback_accepts_articles_below_category_path():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RedUno",
        url="https://www.reduno.com.bo/noticias/nacionales",
    )

    assert scraper._looks_like_article_url(
        "https://www.reduno.com.bo/noticias/magisterio-ratifica-paro-2026510124459",
        source,
    )
    assert not scraper._looks_like_article_url(
        "https://www.reduno.com.bo/noticias/nacionales",
        source,
    )


def test_article_url_filter_rejects_program_pages():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RedBolivision",
        url="https://www.redbolivision.tv.bo/",
    )

    assert not scraper._looks_like_article_url(
        "https://www.redbolivision.tv.bo/programa/la-cancha-de-bolivision/",
        source,
    )


def test_filter_usable_articles_drops_title_only_results():
    scraper = NewsScraper(sources=[])
    source = NewsSource(name="RedBolivision", url="https://www.redbolivision.tv.bo/")

    articles = scraper._filter_usable_articles(
        [
            {
                "title": "La Cancha de Bolivision",
                "url": "https://www.redbolivision.tv.bo/programa/la-cancha-de-bolivision/",
                "description": "",
                "content": None,
            },
            {
                "title": "Noticia con desarrollo",
                "url": "https://www.redbolivision.tv.bo/noticia-real/",
                "description": "La nota incluye informacion suficiente para entender el hecho.",
                "content": "",
            },
        ],
        source,
    )

    assert [article["title"] for article in articles] == ["Noticia con desarrollo"]


def test_extract_article_cleans_title_and_category_text():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="Example",
        url="https://example.com/",
        title_selector="h2 a",
        url_selector="h2 a",
        category_selector=".category",
    )
    soup = BeautifulSoup(
        """
        <article>
          <span class="category">Pol&iacute;tica&nbsp;nacional</span>
          <h2>
            <a href="/news/1">
              Gobierno anunci&oacute; &lt;b&gt;nuevas medidas&lt;/b&gt; para el pa&iacute;s
            </a>
          </h2>
        </article>
        """,
        "lxml",
    )

    article = scraper._extract_article(soup.select_one("article"), source)

    assert article["title"] == "Gobierno anunció nuevas medidas para el país"
    assert article["category"] == "Política nacional"


def test_radio_fides_fallback_extracts_article_until_dateline():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RadioFides",
        url="https://radiofides.com/",
        body_selector=".missing-selector p",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <h1>FEJUVE nacional pide al Gobierno procesar a dirigentes que promueven cercar la ciudad de La Paz</h1>
            <div>Por Radio Fides - 9 mayo, 2026 1 min de lectura</div>
            <div>Tras la amenaza de sectores sociales de cercar completamente la sede de gobierno, la FEJUVE pidio iniciar procesos penales.</div>
            <div>La dirigencia vecinal considera que estas advertencias atentan contra la ciudadania y generan tension.</div>
            <div>/// DPC // LA PAZ ///</div>
            <div>Ultimas noticias</div>
            <div>Este texto lateral no debe entrar.</div>
          </body>
        </html>
        """,
        "lxml",
    )

    content = scraper._extract_body_content(soup, source)

    assert "Tras la amenaza de sectores sociales" in content
    assert "La dirigencia vecinal considera" in content
    assert "texto lateral" not in content


def test_radio_fides_uses_article_title_anchor_not_repeated_sidebar_excerpt():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RadioFides",
        url="https://radiofides.com/",
        body_selector=".entry-content p",
    )
    title = (
        "ESPECIAL: Gobierno anuncia leyes, pero el paquete sobre hidrocarburos, "
        "inversiones y litio se hace esperar"
    )
    soup = BeautifulSoup(
        f"""
        <html>
          <body>
            <section class="entry-content">
              <p>La banca ya empieza a utilizar el dolar referencial y muchas veces programamos transacciones con otro valor.</p>
            </section>
            <nav>Portada Sociedad Nacional Economia Politica Seguridad</nav>
            <h1>{title}</h1>
            <div>Por Radio Fides - 9 mayo, 2026 2 mins de lectura</div>
            <div>A seis meses de gestion del presidente, el Gobierno mantiene pendiente la presentacion del paquete de leyes estructurales.</div>
            <div>Las normas comprometidas apuntan a hidrocarburos, inversiones, litio, mineria y energia para la reactivacion del pais.</div>
            <div>Durante los ultimos meses, distintas autoridades fijaron plazos para el envio de estas iniciativas.</div>
            <div>/// RCL // LA PAZ ///</div>
            <div>Articulos relacionados</div>
          </body>
        </html>
        """,
        "lxml",
    )

    content = scraper._extract_body_content(soup, source, title)

    assert "A seis meses de gestion" in content
    assert "hidrocarburos, inversiones, litio" in content
    assert "La banca ya empieza" not in content


def test_bolivision_fallback_extracts_story_blocks_before_next_title():
    scraper = NewsScraper(sources=[])
    source = NewsSource(
        name="RedBolivision",
        url="https://www.redbolivision.tv.bo/",
        body_selector=".missing-selector p",
    )
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <h1>Persisten los bloqueos en Caranavi: en el municipio de Palos Blancos existen cisternas y camiones parados</h1>
            <h2>La medida afecta el transito y mantiene la interrupcion en la via.</h2>
            <div>El ejecutivo departamental lidera un bloqueo indefinido en la region del norte de La Paz.</div>
            <div>Aunque la medida afecta gravemente la carretera interoceanica, los manifestantes advierten que la protesta continuara.</div>
            <h1>Tarija: otro bus se volco en la ruta hacia Bermejo y 5 personas resultaron heridas</h1>
            <div>Este segundo bloque no debe mezclarse con la primera nota.</div>
          </body>
        </html>
        """,
        "lxml",
    )

    content = scraper._extract_body_content(soup, source)

    assert "El ejecutivo departamental lidera" in content
    assert "carretera interoceanica" in content
    assert "Este segundo bloque" not in content


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
