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


def test_build_prompt_includes_corroborating_articles_as_context():
    summarizer = NewsSummarizer(llm_provider=None)

    prompt = summarizer._build_prompt(
        [
            {
                "title": "Bloqueo indefinido afecta abastecimiento de combustible",
                "description": "Transportistas reportan filas en rutas clave.",
                "source": "MedioA",
                "id": 1,
                "corroborating_articles": [
                    {
                        "title": "El bloqueo ya afecta a tres departamentos",
                        "description": "Autoridades confirman que se extiende a Cochabamba y Oruro.",
                        "source": "MedioB",
                    },
                    {"title": "", "description": "titulo vacio, debe ignorarse"},
                ],
            }
        ],
        "economia",
    )

    assert "Otras fuentes que cubren el mismo hecho" in prompt
    assert "El bloqueo ya afecta a tres departamentos (MedioB)" in prompt
    assert "Autoridades confirman que se extiende a Cochabamba y Oruro." in prompt
    assert "titulo vacio, debe ignorarse" not in prompt


def test_build_prompt_omits_corroborating_section_when_none_present():
    summarizer = NewsSummarizer(llm_provider=None)

    prompt = summarizer._build_prompt(
        [{"title": "Noticia sin duplicados", "description": "Unica fuente.", "id": 1}],
        "general",
    )

    assert "Otras fuentes que cubren el mismo hecho" not in prompt


def test_build_prompt_shows_article_id_for_corroborating_sources():
    summarizer = NewsSummarizer(llm_provider=None)

    prompt = summarizer._build_prompt(
        [
            {
                "title": "Noticia principal",
                "id": 1,
                "corroborating_articles": [
                    {"article_id": 99, "title": "Otra fuente", "source": "MedioB"}
                ],
            }
        ],
        "general",
    )

    assert "[Article ID: 99] Otra fuente (MedioB)" in prompt


def test_parse_response_keeps_valid_claims_with_real_evidence():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        [
          {
            "article_id": 1,
            "title": "Gobierno anuncia bono",
            "summary": "El gobierno anuncio un nuevo bono que se pagara desde marzo segun el ministerio.",
            "claims": [
              {
                "claim": "El bono se paga desde el 15 de marzo",
                "confidence": "multi_source",
                "claim_type": "fecha",
                "article_id": 1,
                "excerpt": "el pago inicia el 15 de marzo"
              }
            ]
          }
        ]
        """,
        "economia",
        [{"id": 1, "title": "Gobierno anuncia bono", "url": "https://a.com/1"}],
    )

    assert summaries[0]["claims"] == [
        {
            "claim": "El bono se paga desde el 15 de marzo",
            "confidence": "multi_source",
            "claim_type": "fecha",
            "article_id": 1,
            "source_url": "https://a.com/1",
            "source_excerpt": "el pago inicia el 15 de marzo",
            "published_at": None,
        }
    ]


def test_parse_response_discards_claim_with_invented_article_id_but_keeps_summary():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        [
          {
            "article_id": 1,
            "title": "Gobierno anuncia bono",
            "summary": "El gobierno anuncio un nuevo bono que se pagara desde marzo segun el ministerio.",
            "claims": [
              {
                "claim": "Dato inventado sin fuente real",
                "confidence": "multi_source",
                "article_id": 999999
              }
            ]
          }
        ]
        """,
        "economia",
        [{"id": 1, "title": "Gobierno anuncia bono", "url": "https://a.com/1"}],
    )

    assert len(summaries) == 1
    assert summaries[0]["claims"][0]["article_id"] == 1
    assert summaries[0]["claims"][0]["source_url"] == "https://a.com/1"


def test_parse_response_normalizes_invalid_confidence_and_caps_claim_count():
    summarizer = NewsSummarizer(llm_provider=None)

    claims_json = ",".join(
        f'{{"claim": "dato {i}", "confidence": "inventado", "article_id": 1}}' for i in range(5)
    )
    summaries = summarizer._parse_response(
        f"""
        [
          {{
            "article_id": 1,
            "title": "Noticia con muchos claims",
            "summary": "Resumen suficientemente largo para pasar la validacion minima del summarizer.",
            "claims": [{claims_json}]
          }}
        ]
        """,
        "general",
        [{"id": 1, "title": "Noticia con muchos claims", "url": "https://a.com/1"}],
    )

    assert len(summaries[0]["claims"]) == summarizer.CLAIM_MAX_COUNT
    assert all(c["confidence"] == "single_source" for c in summaries[0]["claims"])


def test_parse_response_ignores_claims_without_any_valid_evidence_article():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        [
          {
            "title": "Noticia sin id ni url",
            "summary": "Resumen suficientemente largo para pasar la validacion minima del summarizer.",
            "claims": [{"claim": "dato sin fuente citable", "article_id": 5}]
          }
        ]
        """,
        "general",
        [],
    )

    assert summaries[0]["claims"] == []


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
                "title": "Titulo original completo de la fuente",
                "source": "Unitel",
                "url": "https://unitel.bo/noticia",
                "story_cluster_id": "story-42",
                "corroborating_sources": ["unitel", "reduno"],
            }
        ],
    )

    assert summaries == [
        {
            "title": "Titulo original completo de la fuente",
            "summary": "Resumen claro de la noticia.",
            "fact": "Dato clave",
            "category": "politica",
            "article_id": 42,
            "story_cluster_id": "story-42",
            "source_article_count": 2,
            "source": "Unitel",
            "url": "https://unitel.bo/noticia",
            "claims": [],
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
            "story_cluster_id": None,
            "source_article_count": 1,
            "source": "Red Uno",
            "url": "https://reduno.com.bo/noticia",
            "claims": [],
        }
    ]


def test_parse_json_response_extracts_fenced_object_with_summaries():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        Aqui va la respuesta:

        ```json
        {
          "summaries": [
            {
              "article_id": 10,
              "title": "Titulo valido",
              "summary": "Resumen valido de la noticia.",
              "category": "politica"
            }
          ]
        }
        ```
        """,
        "politica",
        [{"id": 10, "title": "Titulo original", "source": "ABI"}],
    )

    assert summaries[0]["article_id"] == 10
    assert summaries[0]["title"] == "Titulo original"
    assert summaries[0]["category"] == "politica"
    assert summaries[0]["source"] == "ABI"


def test_parse_json_response_uses_balanced_array_when_text_contains_brackets():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        Nota editorial [ignorar este texto].
        [
          {
            "title": "Titulo valido",
            "summary": "Resumen valido de la noticia.",
            "category": "general"
          }
        ]
        Texto final [tambien ignorar].
        """,
        "general",
        [],
    )

    assert summaries[0]["title"] == "Titulo valido"
    assert summaries[0]["category"] == "general"


def test_parse_response_forces_requested_category_over_llm_category_drift():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        [
          {
            "title": "Partido de la seleccion",
            "summary": "Resumen valido de la noticia.",
            "category": "cultura"
          }
        ]
        """,
        "deportes",
        [],
    )

    assert summaries[0]["category"] == "deportes"


def test_parse_response_normalizes_generated_category_when_requested_is_invalid():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        [
          {
            "title": "Nueva norma economica",
            "summary": "Resumen valido de la noticia.",
            "category": "Economía"
          }
        ]
        """,
        "",
        [],
    )

    assert summaries[0]["category"] == "economia"


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


def test_parse_response_enriches_short_summary_with_article_context():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        [
          {
            "title": "Control de Vivencia digital",
            "summary": "El tramite se puede hacer desde casa.",
            "fact": "Es obligatorio cada tres meses"
          }
        ]
        """,
        "tecnologia",
        [
            {
                "id": 7,
                "description": (
                    "El tramite obligatorio de tres meses ya se puede efectuar mediante la "
                    "aplicacion movil de la Gestora. Esta dirigido a rentistas y "
                    "derechohabientes que cobran por abono en cuenta."
                ),
            }
        ],
    )

    assert summaries[0]["summary"] == (
        "El tramite se puede hacer desde casa. El tramite obligatorio de tres meses ya "
        "se puede efectuar mediante la aplicacion movil de la Gestora."
    )
    assert len(summaries[0]["summary"]) >= summarizer.SUMMARY_MIN_CHARS


def test_parse_response_uses_generated_title_when_original_is_missing():
    summarizer = NewsSummarizer(llm_provider=None)

    summaries = summarizer._parse_response(
        """
        [
          {
            "title": "Titulo generado",
            "summary": "Resumen claro de la noticia."
          }
        ]
        """,
        "general",
        [],
    )

    assert summaries[0]["title"] == "Titulo generado"
