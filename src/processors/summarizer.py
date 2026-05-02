from typing import Optional

from loguru import logger


class NewsSummarizer:
    """Resume noticias usando IA."""

    SYSTEM_PROMPT = """Eres un editor de noticias experto en español latinoamericano.
Tu tarea es resumir noticias de forma clara, objetiva y concisa.

Cada resumen debe tener:
- Título destacado (máx 100 caracteres)
- 2-3 líneas de lo más importante (máx 200 caracteres)
- Un dato relevante o dato clave

Sé preciso, no agregues opiniones personales.
Responde en español."""

    def __init__(self, llm_provider):
        self.llm = llm_provider

    async def summarize(self, news: list[dict], category: str) -> list[dict]:
        """Resume una lista de noticias por categoría."""

        if not news:
            return []

        prompt = self._build_prompt(news, category)

        try:
            result = await self.llm.chat(
                prompt=prompt,
                quality="quality",
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=3000,
            )

            summaries = self._parse_response(result, category)
            logger.info(
                f"Resumidas {len(summaries)} noticias de categoría '{category}'"
            )
            return summaries

        except Exception as e:
            logger.error(f"Error resumiendo noticias: {e}")
            return []

    def _build_prompt(self, news: list[dict], category: str) -> str:
        """Construye el prompt para la IA."""

        prompt = f"Resume las siguientes noticias de {category.upper()} en Bolivia:\n\n"

        for i, article in enumerate(news[:10], 1):
            title = article.get("title", "")
            description = article.get("description", "")
            source = article.get("source", "")

            prompt += f"{i}. {title}\n"
            if description:
                prompt += f"   {description[:200]}\n"
            prompt += f"   Fuente: {source}\n\n"

        prompt += "\nFormato de respuesta (cada noticia en una línea):"
        prompt += "\nNÚMERO. Título | Resumen | Dato relevante"

        return prompt

    def _parse_response(self, response: str, category: str) -> list[dict]:
        """Parsea la respuesta de la IA."""

        summaries = []

        for line in response.split("\n"):
            line = line.strip()
            if not line:
                continue

            if line[0].isdigit() and "." in line:
                parts = line.split(".", 1)
                if len(parts) > 1:
                    content = parts[1].strip()
                    if "|" in content:
                        subparts = content.split("|")

                        title = subparts[0].strip()[:100]
                        summary = subparts[1].strip()[:200] if len(subparts) > 1 else ""
                        fact = subparts[2].strip()[:100] if len(subparts) > 2 else ""

                        summaries.append(
                            {
                                "title": title,
                                "summary": summary,
                                "fact": fact,
                                "category": category,
                            }
                        )

        return summaries
