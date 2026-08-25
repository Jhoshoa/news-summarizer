from __future__ import annotations

from collections.abc import Iterable

CONFIDENCE_LABELS: dict[str, str] = {
    "corrected": "Corregido después de publicación",
    "contradictory": "Existen versiones contradictorias",
    "official_statement": "Basado en comunicado oficial",
    "multi_source": "Confirmado por varias fuentes",
    "single_source": "Reportado por una sola fuente",
    "developing": "Información en desarrollo",
}


def classify_story_confidence(
    *,
    source_count: int,
    article_count: int,
    current_status: str | None = None,
    relationship_types: Iterable[str] = (),
) -> dict[str, str]:
    """Etiqueta de confianza explicable para una historia (Fase 2.4).

    Deriva la etiqueta de senales que ya existen (source_count, article_count,
    current_status, relationship_type de los articulos que la componen), sin
    modelo de ML adicional. Algunas ramas (corrected/contradictory/
    official_statement) no son alcanzables todavia con los datos actuales
    (nada asigna esos current_status ni ese relationship_type aun), pero la
    funcion queda lista para que Fase 2.5 (correcciones) y una clasificacion
    mas fina de relationship_type las activen sin tocar esta logica.
    """

    status = str(current_status or "").strip().lower()
    types = {str(t or "").strip().lower() for t in relationship_types}

    if status == "corrected":
        level = "corrected"
    elif status == "contradictory":
        level = "contradictory"
    elif "official_statement" in types:
        level = "official_statement"
    elif source_count >= 2:
        level = "multi_source"
    elif source_count <= 1 and article_count <= 1:
        level = "single_source"
    else:
        level = "developing"

    return {"level": level, "label": CONFIDENCE_LABELS[level]}
