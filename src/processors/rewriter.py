from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm.client import LLMProvider

from loguru import logger


class NewsRewriter:
    """Reescribe/normaliza el estilo de las noticias."""

    SYSTEM_PROMPT = """Eres un editor de noticias profesional.
Tu tarea es reescribir los resúmenes en un estilo consistente:

- Tono: profesional pero accesible
- Persona: tercera persona
- Oraciones: cortas y directas
- Sin opiniones personales
- Español latinoamericano neutral

Mejora la claridad sin cambiar los hechos."""

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
        prompt += "\nNÚMERO. Título reescrito | Resumen reescrito"

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
                base["title"] = subparts[0].strip()[:100]
                base["summary"] = subparts[1].strip()[:200]
                base["category"] = base.get("category", "general")
                base["fact"] = base.get("fact", "")
                rewritten.append(base)
                original_index += 1

        if not rewritten:
            return original

        return rewritten
