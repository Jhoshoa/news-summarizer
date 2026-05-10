from src.processors.rewriter import NewsRewriter


def test_parse_response_preserves_original_summary_metadata():
    rewriter = NewsRewriter(llm_provider=None)

    rewritten = rewriter._parse_response(
        "1. Titulo reescrito | Resumen reescrito",
        [
            {
                "title": "Titulo original",
                "summary": "Resumen original",
                "fact": "Dato original",
                "category": "politica",
                "article_id": 123,
                "source": "Unitel",
                "url": "https://unitel.bo/noticia",
            }
        ],
    )

    assert rewritten == [
        {
            "title": "Titulo reescrito",
            "summary": "Resumen reescrito",
            "fact": "Dato original",
            "category": "politica",
            "article_id": 123,
            "source": "Unitel",
            "url": "https://unitel.bo/noticia",
        }
    ]


def test_parse_response_ignores_preface_without_shifting_metadata():
    rewriter = NewsRewriter(llm_provider=None)

    rewritten = rewriter._parse_response(
        "Listo:\n1. Titulo reescrito | Resumen reescrito",
        [
            {
                "title": "Titulo original",
                "summary": "Resumen original",
                "article_id": 55,
                "source": "Source",
                "url": "https://example.com/source",
            }
        ],
    )

    assert rewritten[0]["article_id"] == 55
    assert rewritten[0]["url"] == "https://example.com/source"
