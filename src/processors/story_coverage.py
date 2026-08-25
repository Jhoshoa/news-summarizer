from __future__ import annotations

from collections.abc import Iterable

CLAIM_CONFIDENCE_BUCKETS = ("multi_source", "official_statement", "single_source")


def build_coverage_summary(
    *,
    sources: Iterable[str],
    claims: Iterable[dict],
) -> dict:
    """Comparacion de cobertura de una historia (Fase 2.3): que fuentes la
    reportaron y que tan confirmado esta cada afirmacion puntual, derivado de
    los datos que ya existen (Fase 2.1 fuentes, Fase 2.2 claims) sin
    necesitar un modelo o llamada de IA nueva.

    No incluye deteccion de contradicciones: eso requeriria comparar el
    contenido semantico de claims entre si, para lo cual hoy no hay senal
    (cada claim tiene un solo articulo de evidencia). Mejor omitirlo que
    fingir una comparacion que no se esta haciendo de verdad.
    """

    sources_list = sorted({str(s).strip() for s in sources if str(s or "").strip()})

    buckets: dict[str, list[dict]] = {key: [] for key in CLAIM_CONFIDENCE_BUCKETS}
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        level = str(claim.get("confidence") or "").strip().lower()
        buckets.get(level, buckets["single_source"]).append(claim)

    return {
        "source_count": len(sources_list),
        "sources": sources_list,
        "confirmed_by_multiple_sources": buckets["multi_source"],
        "based_on_official_statement": buckets["official_statement"],
        "reported_by_single_source": buckets["single_source"],
    }
