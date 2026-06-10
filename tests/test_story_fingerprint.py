from src.processors.story_fingerprint import (
    build_canonical_key,
    build_content_fingerprint,
    normalize_story_text,
    story_similarity,
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
