import json
import logging
import re
from collections.abc import Sequence
from typing import Any

logger = logging.getLogger(__name__)

CONTENT_EXCERPT_LIMIT = 500
DEDUP_TEMPERATURE = 0.2


class AIStoryDeduplicator:
    """Uses AI to detect articles covering the same story/event but with
    different wording. Can optionally compare against already-summarized
    stories to avoid redundant summaries across pipeline runs."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    async def deduplicate(
        self, articles: Sequence[dict], existing_summaries: Sequence[dict] | None = None
    ) -> list[dict]:
        if not articles:
            return []
        if existing_summaries:
            return await self._deduplicate_against_summaries(articles, existing_summaries)
        if len(articles) <= 1:
            return list(articles)

        prompt = self._build_prompt(articles)
        try:
            result = await self._llm.chat(
                prompt=prompt,
                quality="fast",
                temperature=DEDUP_TEMPERATURE,
                max_tokens=1000,
            )
            discard_indices = self._parse_indices(result, len(articles))
            if not discard_indices:
                return list(articles)
            return [a for i, a in enumerate(articles) if i not in discard_indices]
        except Exception as e:
            logger.warning("AI dedup fallo, manteniendo todos los articulos: %s", e)
            return list(articles)

    async def _deduplicate_against_summaries(
        self, articles: Sequence[dict], existing_summaries: Sequence[dict]
    ) -> list[dict]:
        prompt = self._build_dedup_against_summaries_prompt(articles, existing_summaries)
        try:
            result = await self._llm.chat(
                prompt=prompt,
                quality="fast",
                temperature=DEDUP_TEMPERATURE,
                max_tokens=1000,
            )
            discard_indices = self._parse_indices(result, len(articles))
            if not discard_indices:
                return list(articles)
            return [a for i, a in enumerate(articles) if i not in discard_indices]
        except Exception as e:
            logger.warning("AI dedup contra summaries fallo, manteniendo todos: %s", e)
            return list(articles)

    def _build_dedup_against_summaries_prompt(
        self, articles: Sequence[dict], existing_summaries: Sequence[dict]
    ) -> str:
        lines = [
            "Eres un asistente que identifica noticias que cubren el MISMO evento o historia",
            "que otras ya resumidas hoy.",
            "",
            "A continuacion se muestran resumenes YA EXISTENTES de noticias de hoy.",
            "Luego, una lista de NUEVOS articulos candidatos a resumir.",
            "",
            "Objetivo: evitar duplicados reales sin perder hechos nuevos.",
            "Se conservan los articulos cuando exista duda razonable.",
            "Prioriza falsos negativos sobre falsos positivos: es preferible conservar",
            "un articulo algo parecido antes que descartar una actualizacion real.",
            "",
            "Reglas:",
            "- Un nuevo articulo es REDUNDANTE SOLO si cubre el mismo hecho verificable",
            "  que algun resumen ya existente: misma accion principal, mismas entidades",
            "  clave y mismos detalles decisivos (fecha, lugar, monto, resultado o medida).",
            "  EJ: 'BCB sube tasa de interes a 7.5%' y 'Banco Central incrementa tasa a 7.5%'",
            "      son redundantes porque describen la misma decision y la misma cifra.",
            "- Tambien es REDUNDANTE si cambia la redaccion pero no cambia el hecho central.",
            "  EJ: 'Shakira y Manuel Garcia-Rulfo fueron vistos juntos y desatan rumores'",
            "      y 'Shakira y Manuel Garcia encienden las redes y desatan rumores'",
            "      hablan del MISMO rumor de romance (mismas personas, mismo hecho).",
            "- Tambien es REDUNDANTE si reporta la misma reunion, operativo, audiencia,",
            "  partido, anuncio o accidente con la misma hora/lugar/resultado.",
            "  EJ: 'Dialogo Gobierno-COB se reprograma para las 16:00 en el BCB'",
            "      y 'Gobierno y COB instalaran el dialogo a las 16:00 en el Banco Central'",
            "      cubren la MISMA reunion (mismos actores, misma hora, mismo lugar).",
            "",
            "NO descartes un articulo por coincidencia de palabras, categoria, lugar o entidades.",
            "- NO es redundante si solo comparte el tema general.",
            "  EJ: 'Gobierno anuncia nuevo bono' vs 'Gobierno evalua eliminar bono'",
            "      son hechos distintos aunque ambos traten de bonos.",
            "- NO es redundante si las mismas personas u organizaciones aparecen en",
            "  acciones diferentes, decisiones opuestas, etapas distintas o consecuencias nuevas.",
            "  EJ: 'Ministro anuncia dialogo con la COB' vs 'COB rechaza propuesta del Gobierno'",
            "      NO son redundantes: mismos actores, acciones y resultado distintos.",
            "  EJ: 'Alcalde niega renuncia' vs 'Concejo acepta renuncia del alcalde'",
            "      NO son redundantes: misma persona, hecho institucional distinto.",
            "- NO es redundante si un articulo agrega una novedad concreta posterior:",
            "  nueva cifra, nuevo detenido, nueva medida, nueva fecha, nueva declaracion",
            "  relevante, cambio de estado, resultado o consecuencia.",
            "- NO es redundante si pertenece a un tema en desarrollo pero informa una",
            "  etapa nueva: respuesta oficial, denuncia, allanamiento, audiencia, protesta,",
            "  normalizacion, incumplimiento, carta, convocatoria o decision posterior.",
            "- TAMPOCO es redundante si habla de las mismas organizaciones pero con",
            "  un enfoque o angulo noticioso diferente (opiniones, reacciones, contexto)",
            "  y no del mismo evento concreto.",
            "  EJ: 'Unos respaldan la negociacion con la COB y otros exigen desbloquear'",
            "      NO es el mismo evento que 'Dialogo Gobierno-COB se reprograma a las 16:00'",
            "      aunque ambos mencionen COB y Gobierno (uno son reacciones, otro es un hecho concreto).",
            "",
            "Criterio de decision: descarta solo cuando el articulo nuevo no aportaria",
            "un hecho noticioso distinto frente al resumen existente.",
            "- Indica SOLO los indices de los articulos NUEVOS que deberian DESCARTARSE",
            "  por ser redundantes con resumenes existentes.",
            "",
            "Formato de respuesta: SOLO un array JSON de indices a descartar, nada mas.",
            "Ejemplo: [0, 3]",
            "Si ninguno es redundante, responde: []",
            "",
            "=== RESUMENES YA EXISTENTES ===",
        ]
        for i, summary in enumerate(existing_summaries):
            title = summary.get("title", "") or ""
            summary_text = summary.get("summary", "") or ""
            category = summary.get("category", "") or ""
            lines.append(f"\n[R{i}] Titulo: {title}")
            if summary_text:
                lines.append(f"    Resumen: {summary_text[:CONTENT_EXCERPT_LIMIT]}")
            lines.append(f"    Categoria: {category}")

        lines.append("")
        lines.append("=== NUEVOS ARTICULOS CANDIDATOS ===")
        self._append_article_lines(lines, articles)
        return "\n".join(lines)

    def _build_prompt(self, articles: Sequence[dict]) -> str:
        lines = [
            "Eres un asistente que identifica noticias que cubren el MISMO evento o historia.",
            "Dada una lista de articulos con indice, titulo, fuente y categoria, determina cuales",
            "hablan del mismo hecho noticioso especifico (no solo del mismo tema general).",
            "",
            "Objetivo: evitar duplicados reales sin perder hechos nuevos.",
            "Se conservan los articulos cuando exista duda razonable.",
            "Prioriza falsos negativos sobre falsos positivos: es preferible conservar",
            "un articulo algo parecido antes que descartar una actualizacion real.",
            "",
            "Reglas:",
            "- Dos articulos son la MISMA HISTORIA SOLO si reportan el mismo hecho verificable:",
            "  misma accion principal, mismas entidades clave y mismos detalles decisivos",
            "  (fecha, lugar, monto, resultado o medida).",
            "  EJ: 'BCB sube tasa de interes a 7.5%' y 'Banco Central incrementa tasa a 7.5%'",
            "      son la misma historia porque describen la misma decision y la misma cifra.",
            "- Tambien son la MISMA HISTORIA si cambia la redaccion pero no cambia el hecho central.",
            "  EJ: 'Shakira y Manuel Garcia-Rulfo fueron vistos juntos y desatan rumores'",
            "      y 'Shakira y Manuel Garcia encienden las redes y desatan rumores'",
            "      hablan del MISMO rumor (mismas personas, mismo hecho).",
            "- Tambien son la MISMA HISTORIA si reportan la misma reunion, operativo, audiencia,",
            "  partido, anuncio o accidente con la misma hora/lugar/resultado.",
            "  EJ: 'Dialogo Gobierno-COB se reprograma para las 16:00 en el BCB'",
            "      y 'Gobierno y COB instalaran el dialogo a las 16:00 en el Banco Central'",
            "      cubren la MISMA reunion (mismos actores, misma hora, mismo lugar).",
            "",
            "NO descartes un articulo por coincidencia de palabras, categoria, lugar o entidades.",
            "- NO son la misma historia si solo comparten el tema general",
            "  (ej: 'Gobierno anuncia nuevo bono' vs 'Gobierno evalua eliminar bono'",
            "  son historias distintas aunque ambas sean sobre bonos).",
            "- NO son la misma historia si las mismas personas u organizaciones aparecen en",
            "  acciones diferentes, decisiones opuestas, etapas distintas o consecuencias nuevas.",
            "  EJ: 'Ministro anuncia dialogo con la COB' vs 'COB rechaza propuesta del Gobierno'",
            "      NO son redundantes: mismos actores, acciones y resultado distintos.",
            "  EJ: 'Alcalde niega renuncia' vs 'Concejo acepta renuncia del alcalde'",
            "      NO son redundantes: misma persona, hecho institucional distinto.",
            "- NO son la misma historia si un articulo agrega una novedad concreta posterior:",
            "  nueva cifra, nuevo detenido, nueva medida, nueva fecha, nueva declaracion",
            "  relevante, cambio de estado, resultado o consecuencia.",
            "- NO son la misma historia si pertenecen a un tema en desarrollo pero informan",
            "  etapas nuevas: respuesta oficial, denuncia, allanamiento, audiencia, protesta,",
            "  normalizacion, incumplimiento, carta, convocatoria o decision posterior.",
            "- TAMPOCO son la misma historia si hablan de las mismas organizaciones pero",
            "  con un enfoque o angulo noticioso diferente (opiniones, reacciones, contexto)",
            "  y no del mismo evento concreto.",
            "  EJ: 'Unos respaldan la negociacion con la COB y otros exigen desbloquear'",
            "      NO es el mismo evento que 'Dialogo Gobierno-COB se reprograma a las 16:00'",
            "      aunque ambos mencionen COB y Gobierno.",
            "",
            "Criterio de decision: descarta solo cuando el articulo no aportaria",
            "un hecho noticioso distinto frente a otro candidato.",
            "- Para cada grupo de articulos que cubran la misma historia, indica los indices",
            "  de los articulos que deberian DESCARTARSE (los redundantes).",
            "",
            "Formato de respuesta: SOLO un array JSON de indices a descartar, nada mas.",
            "Ejemplo: [0, 3]",
            "Si todos son historias unicas, responde: []",
            "",
            "Articulos:",
        ]
        self._append_article_lines(lines, articles)
        return "\n".join(lines)

    def _append_article_lines(self, lines: list[str], articles: Sequence[dict]) -> None:
        for i, article in enumerate(articles):
            title = article.get("title", "") or ""
            source = article.get("source") or article.get("source_name") or ""
            category = article.get("category", "") or ""
            content = (
                article.get("content_excerpt")
                or article.get("description")
                or article.get("summary")
                or ""
            )
            if len(content) > CONTENT_EXCERPT_LIMIT:
                content = content[:CONTENT_EXCERPT_LIMIT] + "..."
            lines.append(f"\n[{i}] Titulo: {title}")
            lines.append(f"    Fuente: {source}")
            lines.append(f"    Categoria: {category}")
            lines.append(f"    Extracto: {content}")

    def _parse_indices(self, response: str, total: int) -> set[int]:
        if not response or not response.strip():
            return set()
        cleaned = response.strip()

        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        if cleaned.startswith("JSON"):
            cleaned = cleaned[4:].strip()

        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return {
                    int(i)
                    for i in data
                    if isinstance(i, (int, float)) and 0 <= int(i) < total
                }
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        match = re.search(r"\[[\d,\s]+\]", cleaned)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, list):
                    return {
                        int(i)
                        for i in data
                        if isinstance(i, (int, float)) and 0 <= int(i) < total
                    }
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        nums = re.findall(r"\b(\d+)\b", cleaned)
        parsed = {int(n) for n in nums if 0 <= int(n) < total}
        if parsed:
            return parsed

        return set()
