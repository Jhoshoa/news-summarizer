import json
import re
from typing import Any

from loguru import logger


class NewsSummarizer:
    """Resume noticias usando IA."""

    SYSTEM_PROMPT = """Eres un editor de noticias experto en espanol latinoamericano.
Tu tarea es resumir noticias de forma clara, objetiva y concisa.

Cada resumen debe tener:
- Titulo destacado (max 100 caracteres)
- 2-3 lineas de lo mas importante (max 200 caracteres)
- Un dato relevante o dato clave

Se preciso, no agregues opiniones personales.
Responde en espanol.
Devuelve solo JSON valido, sin markdown ni texto adicional."""

    def __init__(self, llm_provider):
        self.llm = llm_provider

    async def summarize(self, news: list[dict], category: str) -> list[dict]:
        """Resume una lista de noticias por categoria."""

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

            summaries = self._parse_response(result, category, news)
            logger.info(f"Resumidas {len(summaries)} noticias de categoria '{category}'")
            return summaries

        except Exception as e:
            logger.error(f"Error resumiendo noticias: {e}")
            return []

    def _build_prompt(self, news: list[dict], category: str) -> str:
        """Construye el prompt para la IA."""

        prompt = f"Resume las siguientes noticias de {category.upper()} en Bolivia:\n\n"

        for i, article in enumerate(news[:10], 1):
            article_id = article.get("id") or article.get("article_id")
            title = article.get("title", "")
            description = article.get("description", "")
            url = article.get("url", "")
            source = article.get("source", "")
            content = article.get("content") or article.get("excerpt") or ""
            published_at = article.get("published_at")

            prompt += f"{i}. {title}\n"
            if article_id is not None:
                prompt += f"   Article ID: {article_id}\n"
            if description:
                prompt += f"   Descripcion: {description[:200]}\n"
            if content:
                prompt += f"   Detalle: {self._truncate_content(content)}\n"
            if url:
                prompt += f"   URL: {url}\n"
            if published_at:
                prompt += f"   Publicado: {published_at}\n"
            prompt += f"   Fuente: {source}\n\n"

        prompt += "\nDevuelve un arreglo JSON con un objeto por noticia:"
        prompt += """
[
  {
    "article_id": 123,
    "title": "Titulo destacado",
    "summary": "Resumen claro en 2-3 lineas",
    "fact": "Dato relevante",
    "category": "politica",
    "source": "Nombre de la fuente",
    "url": "https://..."
  }
]"""

        return prompt

    def _truncate_content(self, content: str, max_length: int = 900) -> str:
        content = " ".join(str(content).split())
        if len(content) <= max_length:
            return content

        return content[:max_length].rsplit(" ", 1)[0].strip()

    def _parse_response(
        self,
        response: str,
        category: str,
        original_news: list[dict] | None = None,
    ) -> list[dict]:
        """Parsea la respuesta de la IA."""

        original_news = original_news or []
        parsed = self._parse_json_response(response)
        if parsed is not None:
            summaries = self._normalize_json_summaries(parsed, category, original_news)
            if summaries:
                return summaries

            logger.warning("LLM JSON response did not contain valid summaries")

        return self._parse_legacy_response(response, category, original_news)

    def _parse_json_response(self, response: str) -> list[Any] | None:
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            data = self._extract_json_array(response)

        if isinstance(data, dict):
            data = data.get("summaries") or data.get("items") or data.get("data")

        return data if isinstance(data, list) else None

    def _extract_json_array(self, response: str) -> list[Any] | None:
        match = re.search(r"\[[\s\S]*\]", response)
        if not match:
            logger.warning("LLM response did not include a JSON array")
            return None

        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid LLM JSON response: {e}")
            return None

        return data if isinstance(data, list) else None

    def _normalize_json_summaries(
        self,
        items: list[Any],
        category: str,
        original_news: list[dict],
    ) -> list[dict]:
        summaries = []

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                logger.warning(f"Ignoring malformed summary item at index {index}: {item}")
                continue

            original = self._find_original_article(item, original_news, index)
            title = self._clean_generated_text(item.get("title") or original.get("title") or "")[:100]
            summary = self._clean_generated_text(item.get("summary") or "")[:200]

            if not title or not summary:
                logger.warning(f"Ignoring incomplete summary item at index {index}: {item}")
                continue

            summaries.append(
                {
                    "title": title,
                    "summary": summary,
                    "fact": self._clean_generated_text(item.get("fact") or "")[:100],
                    "category": str(item.get("category") or category).strip().lower(),
                    "article_id": item.get("article_id")
                    or original.get("id")
                    or original.get("article_id"),
                    "source": item.get("source") or original.get("source"),
                    "url": item.get("url") or original.get("url"),
                }
            )

        return summaries

    def _find_original_article(
        self,
        item: dict,
        original_news: list[dict],
        fallback_index: int,
    ) -> dict:
        article_id = item.get("article_id")
        if article_id is not None:
            for article in original_news:
                if str(article.get("id") or article.get("article_id")) == str(article_id):
                    return article

        if fallback_index < len(original_news):
            return original_news[fallback_index]

        return {}

    def _parse_legacy_response(
        self,
        response: str,
        category: str,
        original_news: list[dict],
    ) -> list[dict]:
        """Parsea la respuesta de la IA en el formato anterior."""

        summaries = []

        for index, line in enumerate(response.split("\n")):
            line = line.strip()
            if not line:
                continue

            if line[0].isdigit() and "." in line:
                parts = line.split(".", 1)
                if len(parts) <= 1:
                    continue

                content = parts[1].strip()
                if "|" not in content:
                    continue

                subparts = content.split("|")
                original = original_news[index] if index < len(original_news) else {}

                summaries.append(
                    {
                        "title": self._clean_generated_text(subparts[0])[:100],
                        "summary": self._clean_generated_text(subparts[1])[:200]
                        if len(subparts) > 1
                        else "",
                        "fact": self._clean_generated_text(subparts[2])[:100]
                        if len(subparts) > 2
                        else "",
                        "category": category,
                        "article_id": original.get("id") or original.get("article_id"),
                        "source": original.get("source"),
                        "url": original.get("url"),
                    }
                )

        return summaries

    def _clean_generated_text(self, value: Any) -> str:
        text = str(value or "").strip()
        text = re.sub(r"^\s*(?:\d+[\.)]\s*)+", "", text)
        return re.sub(r"\s+", " ", text).strip()
