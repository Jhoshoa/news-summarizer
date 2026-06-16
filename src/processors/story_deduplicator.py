import json
import logging
import re
from collections.abc import Sequence
from typing import Any

logger = logging.getLogger(__name__)


class AIStoryDeduplicator:
    """Uses AI to detect articles covering the same story/event but with
    different wording. Keeps only the highest-ranked article per story
    cluster. Original title, article_id, and all fields from the kept
    article are preserved unchanged."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    async def deduplicate(self, articles: Sequence[dict]) -> list[dict]:
        if len(articles) <= 1:
            return list(articles)

        prompt = self._build_prompt(articles)
        try:
            result = await self._llm.chat(
                prompt=prompt,
                quality="fast",
                temperature=0.1,
                max_tokens=1000,
            )
            discard_indices = self._parse_indices(result, len(articles))
            if not discard_indices:
                return list(articles)
            return [a for i, a in enumerate(articles) if i not in discard_indices]
        except Exception as e:
            logger.warning("AI dedup fallo, manteniendo todos los articulos: %s", e)
            return list(articles)

    def _build_prompt(self, articles: Sequence[dict]) -> str:
        lines = [
            "Eres un asistente que identifica noticias que cubren el MISMO evento o historia.",
            "Dada una lista de artículos con índice, título, fuente y categoría, determina cuáles",
            "hablan del mismo hecho noticioso específico (no solo del mismo tema general).",
            "",
            "Reglas:",
            "- Dos artículos son la MISMA HISTORIA si reportan el mismo evento específico",
            "  con el mismo sujeto/objeto y cifras (ej: 'BCB sube tasa de interés a 7.5%'",
            "  y 'Banco Central incrementa tasa a 7.5%' cubren el mismo evento).",
            "- NO son la misma historia si solo comparten el tema general",
            "  (ej: 'Gobierno anuncia nuevo bono' vs 'Gobierno evalúa eliminar bono'",
            "  son historias distintas aunque ambas sean sobre bonos).",
            "- Para cada grupo de artículos que cubran la misma historia, indica los índices",
            "  de los artículos que deberían DESCARTARSE (los redundantes).",
            "",
            "Formato de respuesta: SOLO un array JSON de índices a descartar, nada más.",
            "Ejemplo: [0, 3]",
            "Si todos son historias únicas, responde: []",
            "",
            "Artículos:",
        ]
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
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"\n[{i}] Titulo: {title}")
            lines.append(f"    Fuente: {source}")
            lines.append(f"    Categoria: {category}")
            lines.append(f"    Extracto: {content}")
        return "\n".join(lines)

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
