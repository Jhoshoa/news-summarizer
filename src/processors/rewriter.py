import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llm.client import LLMProvider

from loguru import logger


class NewsRewriter:
    """Reescribe/normaliza el estilo de las noticias."""

    TITLE_MAX_CHARS = 100
    SUMMARY_MAX_CHARS = 360

    SYSTEM_PROMPT = """Eres un editor de noticias profesional.
Tu tarea es reescribir los resúmenes en un estilo consistente:

- Tono: profesional pero accesible
- Persona: tercera persona
- Resumenes: 2 oraciones con contexto suficiente, entre 180 y 320 caracteres
- Oraciones: claras y directas
- Sin opiniones personales
- Español latinoamericano neutral

Mejora la claridad sin cambiar los hechos ni recortar contexto relevante."""

    def __init__(self, llm_provider: "LLMProvider"):
        self.llm = llm_provider

    async def rewrite(self, summaries: list[dict]) -> list[dict]:
        """Reescribe una lista de resúmenes."""

        if not summaries:
            return []

        prompt = self._build_prompt(summaries)

        try:
            result = await self.llm.chat(
                prompt=prompt,
                quality="fast",
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=2000,
            )

            rewritten = self._parse_response(result, summaries)
            logger.info(f"Reescritos {len(rewritten)} resúmenes")
            return rewritten

        except Exception as e:
            logger.error(f"Error reescribiendo resúmenes: {e}")
            return summaries

    def _build_prompt(self, summaries: list[dict]) -> str:
        """Construye el prompt para reescribir."""

        prompt = "Reescribe los siguientes resúmenes en estilo consistente:\n\n"

        for i, article in enumerate(summaries, 1):
            title = article.get("title", "")
            summary = article.get("summary", "")
            category = article.get("category", "")

            prompt += f"{i}. [{category}] {title}: {summary}\n"

        prompt += "\nFormato de respuesta:"
        prompt += "\nNÚMERO. Título reescrito | Resumen reescrito en 2 oraciones con contexto"

        return prompt

    def _parse_response(self, response: str, original: list[dict]) -> list[dict]:
        """Parsea la respuesta reescrita."""

        rewritten = []
        original_index = 0

        for line in response.split("\n"):
            line = line.strip()
            if not line or not line[0].isdigit():
                continue

            parts = line.split(".", 1)
            if len(parts) > 1 and "|" in parts[1]:
                subparts = parts[1].split("|")

                base = dict(original[original_index]) if original_index < len(original) else {}
                base["title"] = self._limit_text(
                    self._clean_generated_text(subparts[0]),
                    self.TITLE_MAX_CHARS,
                )
                base["summary"] = self._limit_text(
                    self._clean_generated_text(subparts[1]),
                    self.SUMMARY_MAX_CHARS,
                )
                base["category"] = base.get("category", "general")
                base["fact"] = base.get("fact", "")
                rewritten.append(base)
                original_index += 1

        if not rewritten:
            return original

        return rewritten

    def _clean_generated_text(self, value: Any) -> str:
        text = str(value or "").strip()
        text = re.sub(r"^\s*(?:\d+[\.)]\s*)+", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def _limit_text(self, value: str, max_chars: int) -> str:
        if len(value) <= max_chars:
            return value

        truncated = value[:max_chars].rsplit(" ", 1)[0].strip()
        return truncated or value[:max_chars].strip()
