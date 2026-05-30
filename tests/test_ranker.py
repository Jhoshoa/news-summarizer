from datetime import UTC, datetime, timedelta

from src.processors.ranker import NewsRanker


def _article(**overrides):
    article = {
        "title": "Bloqueo nacional afecta el abastecimiento de combustible en Bolivia",
        "description": "Autoridades reportan impacto economico y dificultades para transportar productos.",
        "content": " ".join(["contenido"] * 180),
        "source": "RedUno",
        "category": "economia",
        "category_confidence": 0.86,
        "published_at": datetime.now(UTC) - timedelta(hours=2),
        "image": "https://example.com/image.jpg",
    }
    article.update(overrides)
    return article


def test_rank_adds_auditable_score_metadata():
    ranker = NewsRanker()

    ranked = ranker.rank([_article()])

    assert ranked[0]["score"] > 0
    assert ranked[0]["score_components"]["impact"] == 100
    assert ranked[0]["score_components"]["corroboration"] == 0
    assert ranked[0]["score_components"]["category_confidence"] == 100
    assert "score_reason" in ranked[0]
    assert "impacto high:bloqueo nacional" in ranked[0]["score_reason"]


def test_high_impact_article_can_outrank_low_impact_article_from_strong_source():
    ranker = NewsRanker()
    high_impact = _article(
        title="Banco Central anuncia medidas por falta de dolar",
        source="RadioFides",
        published_at=datetime.now(UTC) - timedelta(hours=4),
    )
    low_impact = _article(
        title="Celebridad comparte una historia viral en redes sociales",
        description="Una publicacion de entretenimiento genera comentarios entre sus seguidores.",
        content=" ".join(["contenido"] * 180),
        source="Unitel",
        published_at=datetime.now(UTC) - timedelta(minutes=20),
    )

    ranked = ranker.rank([low_impact, high_impact])

    assert ranked[0] is high_impact
    assert high_impact["score_components"]["impact"] == 100
    assert low_impact["score_components"]["impact"] == 0


def test_poor_content_is_penalized():
    ranker = NewsRanker()
    article = _article(
        description="Texto repetido",
        content="Texto repetido",
    )

    ranker.rank([article])

    assert article["score_components"]["penalties"] >= 35
    assert "penalizacion:contenido corto" in article["score_reason"]
    assert "penalizacion:descripcion duplicada" in article["score_reason"]


def test_low_category_confidence_reduces_score():
    ranker = NewsRanker()
    high_confidence = _article(category_confidence=0.9)
    low_confidence = _article(category_confidence=0.2)

    ranker.rank([high_confidence, low_confidence])

    assert high_confidence["score_components"]["category_confidence"] == 100
    assert low_confidence["score_components"]["category_confidence"] == 35
    assert high_confidence["score"] > low_confidence["score"]


def test_missing_config_uses_fallback(tmp_path):
    missing_config = tmp_path / "missing-scoring.yaml"
    ranker = NewsRanker(config_path=missing_config)
    article = _article(source="Radio Fides")

    ranker.rank([article])

    assert article["score_components"]["source"] == 84
    assert "fuente:radiofides" in article["score_reason"]


def test_rank_limit_keeps_highest_scored_articles():
    ranker = NewsRanker()
    important = _article(title="Crisis por combustible afecta a varias regiones")
    minor = _article(
        title="Agenda cultural anuncia actividades para el fin de semana",
        description="La agenda cultural incluye eventos menores y actividades recreativas.",
        content=" ".join(["contenido"] * 80),
        source="NewsAPI",
        category_confidence=0.5,
        published_at=datetime.now(UTC) - timedelta(hours=30),
        image=None,
    )

    ranked = ranker.rank([minor, important], limit=1)

    assert ranked == [important]


def test_similar_articles_from_different_sources_are_clustered_and_corroborated():
    ranker = NewsRanker()
    unitel = _article(
        title="Bloqueo indefinido afecta el abastecimiento de combustible",
        source="Unitel",
    )
    reduno = _article(
        title="Bloqueo indefinido afecta abastecimiento de combustible",
        source="RedUno",
    )
    radiofides = _article(
        title="El bloqueo indefinido complica el abastecimiento de combustible",
        source="RadioFides",
    )

    ranker.rank([unitel, reduno, radiofides])

    assert unitel["cluster_id"] == reduno["cluster_id"] == radiofides["cluster_id"]
    assert unitel["corroborating_sources"] == ["radiofides", "reduno", "unitel"]
    assert unitel["score_components"]["corroboration"] == 100
    assert "corroborada:3 fuentes" in unitel["score_reason"]


def test_unrelated_articles_are_not_clustered():
    ranker = NewsRanker()
    economy = _article(
        title="Tipo de cambio genera preocupacion en el sector productivo",
        source="Unitel",
        category="economia",
    )
    sports = _article(
        title="La seleccion prepara cambios para su proximo partido",
        description="El equipo nacional entrena antes de una nueva fecha internacional.",
        source="RedUno",
        category="deportes",
    )

    ranker.rank([economy, sports])

    assert economy["cluster_id"] != sports["cluster_id"]
    assert economy["score_components"]["corroboration"] == 0
    assert sports["score_components"]["corroboration"] == 0


def test_corroborated_story_can_outrank_isolated_recent_story():
    ranker = NewsRanker()
    isolated_recent = _article(
        title="Anuncio menor genera comentarios en redes sociales",
        description="Una publicacion de entretenimiento se volvio tendencia durante la jornada.",
        content=" ".join(["contenido"] * 180),
        source="Unitel",
        published_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    corroborated_old = _article(
        title="Escasez de combustible afecta al transporte pesado",
        source="RedUno",
        published_at=datetime.now(UTC) - timedelta(hours=5),
    )
    corroborated_pair = _article(
        title="Escasez de combustible golpea al transporte pesado",
        source="RadioFides",
        published_at=datetime.now(UTC) - timedelta(hours=5),
    )

    ranked = ranker.rank([isolated_recent, corroborated_old, corroborated_pair])

    assert ranked[0] is corroborated_old or ranked[0] is corroborated_pair
    assert ranked[0]["score_components"]["corroboration"] == 70
    assert isolated_recent["score_components"]["corroboration"] == 0
