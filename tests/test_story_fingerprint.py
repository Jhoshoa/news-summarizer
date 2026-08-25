from src.processors.story_fingerprint import (
    build_canonical_key,
    build_content_fingerprint,
    build_url_fingerprint,
    normalize_story_text,
    normalize_url,
    story_similarity,
    temporal_proximity_factor,
)


def test_normalize_story_text_removes_accents_punctuation_and_low_value_prefixes():
    assert normalize_story_text("VIDEO: Última hora: Cámara aprueba nueva ley") == (
        "camara aprueba nueva ley"
    )


def test_content_fingerprint_ignores_url_and_source_for_same_story():
    base = {
        "title": "Reportera cae al intentar atrapar regalo de presidenta",
        "description": "La reportera cayo durante una conferencia y el hecho se viralizo.",
        "category": "general",
        "url": "https://example.com/a",
        "source": "Unitel",
    }
    republished = {
        **base,
        "url": "https://other.example.com/b",
        "source": "RedUno",
    }

    assert build_canonical_key(base) == build_canonical_key(republished)
    assert build_content_fingerprint(base) == build_content_fingerprint(republished)


def test_story_similarity_groups_near_duplicate_titles_with_shared_content():
    left = {
        "title": "Bloqueo indefinido afecta abastecimiento de combustible",
        "description": "Transportistas reportan filas y dificultades por el bloqueo en rutas clave.",
        "category": "economia",
    }
    right = {
        "title": "El bloqueo indefinido complica el abastecimiento de combustible",
        "description": "Transportistas reportan filas y dificultades por bloqueo en rutas clave.",
        "category": "economia",
    }

    assert story_similarity(left, right) >= 0.85


def test_normalize_url_ignores_scheme_www_tracking_params_and_trailing_slash():
    left = normalize_url("http://www.example.com/pais/nota/?utm_source=fb&utm_medium=social")
    right = normalize_url("https://example.com/pais/nota?fbclid=abc123")

    assert left == right == "https://example.com/pais/nota"


def test_normalize_url_keeps_non_tracking_query_params_and_sorts_them():
    left = normalize_url("https://example.com/nota?b=2&a=1")
    right = normalize_url("https://example.com/nota?a=1&b=2")

    assert left == right == "https://example.com/nota?a=1&b=2"


def test_normalize_url_treats_different_articles_as_different():
    assert normalize_url("https://example.com/nota-a") != normalize_url(
        "https://example.com/nota-b"
    )


def test_normalize_url_handles_empty_value():
    assert normalize_url(None) == ""
    assert normalize_url("") == ""


def test_build_url_fingerprint_matches_for_normalized_equivalent_urls():
    left = build_url_fingerprint("http://www.example.com/nota/?utm_campaign=x")
    right = build_url_fingerprint("https://example.com/nota")

    assert left == right
    assert build_url_fingerprint(None) == ""


def test_temporal_proximity_factor_is_neutral_when_close_in_time():
    assert temporal_proximity_factor(0.5, window_hours=72) > 0.99


def test_temporal_proximity_factor_decays_near_window_edge():
    factor = temporal_proximity_factor(72, window_hours=72)
    assert 0.84 < factor < 0.86


def test_temporal_proximity_factor_handles_zero_window():
    assert temporal_proximity_factor(10, window_hours=0) == 1.0


def test_story_similarity_keeps_distinct_short_titles_apart():
    left = {
        "title": "Banco Central anuncia nueva cotizacion del dolar",
        "description": "Cotizacion del dolar.",
        "category": "economia",
    }
    right = {
        "title": "Seleccion boliviana prepara cambios para amistoso",
        "description": "Cambios para amistoso.",
        "category": "deportes",
    }

    assert story_similarity(left, right) == 0.0
