from src.processors.summarizer import NewsSummarizer


def test_build_prompt_includes_article_body_excerpt_and_url():
    summarizer = NewsSummarizer(llm_provider=None)

    prompt = summarizer._build_prompt(
        [
            {
                "title": "Gobierno anuncia nuevas medidas economicas",
                "description": "El anuncio fue realizado este domingo.",
                "content": "Primer detalle importante. Segundo detalle con contexto para resumir.",
                "url": "https://example.com/noticia",
                "source": "Example News",
                "id": 123,
                "published_at": "2026-05-10T12:00:00",
            }
        ],
        "economia",
    )

    assert "Gobierno anuncia nuevas medidas economicas" in prompt
    assert "Detalle: Primer detalle importante" in prompt
    assert "URL: https://example.com/noticia" in prompt
    assert "Fuente: Example News" in prompt
    assert "Article ID: 123" in prompt
    assert '"article_id": 123' in prompt


def test_parse_json_response_preserves_article_metadata_from_original_news():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        [
          {
            "article_id": 42,
            "title": "Titulo resumido",
            "summary": "Resumen claro de la noticia.",
            "fact": "Dato clave",
            "category": "politica"
          }
        ]
        """,
        "politica",
        [
            {
                "id": 42,
                "source": "Unitel",
                "url": "https://unitel.bo/noticia",
            }
        ],
    )

    assert summaries == [
        {
            "title": "Titulo resumido",
            "summary": "Resumen claro de la noticia.",
            "fact": "Dato clave",
            "category": "politica",
            "article_id": 42,
            "source": "Unitel",
            "url": "https://unitel.bo/noticia",
        }
    ]


def test_parse_json_response_extracts_array_from_extra_text_and_skips_bad_items():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        Aqui esta el JSON:
        [
          "bad item",
          {"title": "Sin resumen"},
          {
            "title": "Titulo valido",
            "summary": "Resumen valido",
            "source": "Red Uno",
            "url": "https://reduno.com.bo/noticia"
          }
        ]
        """,
        "general",
        [],
    )

    assert summaries == [
        {
            "title": "Titulo valido",
            "summary": "Resumen valido",
            "fact": "",
            "category": "general",
            "article_id": None,
            "source": "Red Uno",
            "url": "https://reduno.com.bo/noticia",
        }
    ]


def test_parse_legacy_response_keeps_article_metadata_as_fallback():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        "1. Titulo viejo | Resumen viejo | Dato viejo",
        "deportes",
        [
            {
                "id": 9,
                "source": "Example",
                "url": "https://example.com/deportes",
            }
        ],
    )

    assert summaries[0]["article_id"] == 9
    assert summaries[0]["source"] == "Example"
    assert summaries[0]["url"] == "https://example.com/deportes"


def test_parse_response_removes_generated_numbering():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        [
          {
            "title": "1. Titulo resumido",
            "summary": "2) Resumen claro",
            "fact": "3. Dato clave"
          }
        ]
        """,
        "politica",
        [],
    )

    assert summaries[0]["title"] == "Titulo resumido"
    assert summaries[0]["summary"] == "Resumen claro"
    assert summaries[0]["fact"] == "Dato clave"
