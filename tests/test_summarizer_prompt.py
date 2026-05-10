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
            }
        ],
        "economia",
    )

    assert "Gobierno anuncia nuevas medidas economicas" in prompt
    assert "Detalle: Primer detalle importante" in prompt
    assert "URL: https://example.com/noticia" in prompt
    assert "Fuente: Example News" in prompt
