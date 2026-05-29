from src.processors.classifier import NewsClassifier


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
