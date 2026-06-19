from src.processors.classifier import NewsClassifier


class FakeClassifierLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    async def chat(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        return self.response


def test_classifier_uses_weighted_rules_for_politics():
    classifier = NewsClassifier()

    decision = classifier.classify_article(
        {
            "title": "El Gobierno promulga una nueva ley electoral",
            "description": "El presidente y el TSE explicaron los cambios para las elecciones.",
            "content": "",
            "category": "general",
        }
    )

    assert decision.category == "politica"
    assert decision.confidence > 0.8
    assert decision.method == "rules"
    assert decision.scores["politica"] > decision.scores["deportes"]


def test_classifier_does_not_treat_political_party_as_sports_match():
    classifier = NewsClassifier()

    decision = classifier.classify_article(
        {
            "title": "Un partido politico presenta candidato para las elecciones",
            "description": "La organizacion anuncio su alianza ante el Tribunal Supremo Electoral.",
            "content": "",
            "category": "general",
        }
    )

    assert decision.category == "politica"
    assert decision.scores["deportes"] == 0


def test_classifier_treats_football_match_as_sports():
    classifier = NewsClassifier()

    decision = classifier.classify_article(
        {
            "title": "Bolivar gana el partido de futbol con dos goles",
            "description": "El club paceño avanzo en el campeonato de la liga profesional.",
            "content": "",
            "category": "general",
        }
    )

    assert decision.category == "deportes"
    assert decision.scores["deportes"] > decision.scores["politica"]


def test_classifier_uses_word_boundaries_for_ia_keyword():
    classifier = NewsClassifier()

    unrelated = classifier.classify_article(
        {
            "title": "La familia participa en una feria barrial",
            "description": "Vecinos asistieron a una actividad cultural.",
            "content": "",
            "category": "general",
        }
    )
    technology = classifier.classify_article(
        {
            "title": "Nueva herramienta de IA ayuda a detectar fraudes",
            "description": "La aplicacion usa inteligencia artificial para analizar datos.",
            "content": "",
            "category": "general",
        }
    )

    assert unrelated.category != "tecnologia"
    assert technology.category == "tecnologia"


def test_classifier_falls_back_to_general_without_enough_signals():
    classifier = NewsClassifier()

    decision = classifier.classify_article(
        {
            "title": "Vecinos participan en una actividad comunitaria",
            "description": "La jornada reunio a familias durante la mañana.",
            "content": "",
            "category": "general",
        }
    )

    assert decision.category == "general"
    assert decision.confidence == 0.0


def test_classify_batch_adds_auditable_metadata():
    classifier = NewsClassifier()
    articles = [
        {
            "title": "El Banco Central informa sobre el tipo de cambio",
            "description": "La autoridad explico nuevas medidas economicas.",
            "content": "",
            "category": "general",
        }
    ]

    result = classifier.classify_batch(articles)

    assert result[0]["category"] == "economia"
    assert result[0]["category_confidence"] > 0
    assert result[0]["category_scores"]["economia"] > 0
    assert result[0]["category_reason"].startswith("economia:")
    assert result[0]["category_method"] == "rules"


def test_classifier_maps_reduno_deportes_source_category():
    classifier = NewsClassifier()

    result = classifier.classify_batch(
        [
            {
                "title": "Equipo local presenta nueva camiseta",
                "description": "La actividad se realizo con hinchas en La Paz.",
                "content": "",
                "source": "RedUno",
                "category": "Deportes",
            }
        ]
    )

    assert result[0]["category"] == "deportes"
    assert result[0]["source_category_raw"] == "deportes"
    assert result[0]["source_category_mapped"] == "deportes"
    assert "source_category:categoria_fuente" in result[0]["category_reason"]


def test_classifier_maps_reduno_nacionales_to_politics():
    classifier = NewsClassifier()

    result = classifier.classify_batch(
        [
            {
                "title": "Autoridades anuncian reunion nacional",
                "description": "El encuentro abordara temas de gestion publica.",
                "content": "",
                "source": "RedUno",
                "category": "Nacionales",
            }
        ]
    )

    assert result[0]["category"] == "politica"
    assert result[0]["source_category_raw"] == "nacionales"
    assert result[0]["source_category_mapped"] == "politica"


def test_classifier_uses_global_source_category_mapping_with_accents():
    classifier = NewsClassifier()

    result = classifier.classify_batch(
        [
            {
                "title": "Empresas reportan nueva actividad productiva",
                "description": "El informe fue presentado durante la jornada.",
                "content": "",
                "source": "Example",
                "category": "Economía",
            }
        ]
    )

    assert result[0]["category"] == "economia"
    assert result[0]["source_category_raw"] == "economia"
    assert result[0]["source_category_mapped"] == "economia"


async def test_classify_batch_async_uses_llm_for_low_confidence_rule():
    llm = FakeClassifierLLM(
        '{"category": "politica", "confidence": 0.81, "reason": "Menciona ley y club civico."}'
    )
    classifier = NewsClassifier(llm_provider=llm)
    articles = [
        {
            "title": "Comision de penal y memoria del sistema",
            "description": "La autoridad reporto perdida de datos",
            "content": "",
            "category": "general",
        }
    ]

    result = await classifier.classify_batch_async(articles)

    assert len(llm.calls) == 1
    assert result[0]["category"] == "politica"
    assert result[0]["category_method"] == "llm_fallback"
    assert result[0]["category_rule_category"] == "politica"
    assert result[0]["category_rule_confidence"] > 0
    assert result[0]["category_reason"].startswith("llm:")


async def test_classify_batch_async_skips_llm_for_confident_rule():
    llm = FakeClassifierLLM('{"category": "general", "confidence": 0.99, "reason": "No usar"}')
    classifier = NewsClassifier(llm_provider=llm)
    articles = [
        {
            "title": "El Gobierno y el TSE coordinan las elecciones nacionales",
            "description": "El presidente y diputados explicaron la nueva ley electoral.",
            "content": "",
            "category": "general",
        }
    ]

    result = await classifier.classify_batch_async(articles)

    assert llm.calls == []
    assert result[0]["category"] == "politica"
    assert result[0]["category_method"] == "rules"


async def test_classify_batch_async_keeps_rules_when_llm_returns_invalid_category():
    llm = FakeClassifierLLM('{"category": "salud", "confidence": 0.95, "reason": "Invalida"}')
    classifier = NewsClassifier(llm_provider=llm)
    articles = [
        {
            "title": "Comision de penal y memoria del sistema",
            "description": "La autoridad reporto perdida de datos",
            "content": "",
            "category": "general",
        }
    ]

    result = await classifier.classify_batch_async(articles)

    assert len(llm.calls) == 1
    assert result[0]["category"] == "politica"
    assert result[0]["category_method"] == "rules_low_confidence"
    assert result[0]["category_llm_error"] == "invalid_category:salud"


async def test_classify_batch_async_parses_llm_json_inside_markdown_fence():
    llm = FakeClassifierLLM(
        '```json\n{"category": "politica", "confidence": 0.77, "reason": "Contexto politico"}\n```'
    )
    classifier = NewsClassifier(llm_provider=llm)
    articles = [
        {
            "title": "Comision de penal y memoria del sistema",
            "description": "La autoridad reporto perdida de datos",
            "content": "",
            "category": "general",
        }
    ]

    result = await classifier.classify_batch_async(articles)

    assert result[0]["category"] == "politica"
    assert result[0]["category_method"] == "llm_fallback"
