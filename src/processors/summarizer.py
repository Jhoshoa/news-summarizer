import json
import re
import unicodedata
from typing import Any

from loguru import logger


class NewsSummarizer:
    """Resume noticias usando IA."""

    TITLE_MAX_CHARS = 100
    SUMMARY_MIN_CHARS = 120
    SUMMARY_MAX_CHARS = 360
    FACT_MAX_CHARS = 140
    CLAIM_MAX_CHARS = 220
    CLAIM_EXCERPT_MAX_CHARS = 160
    CLAIM_MAX_COUNT = 3
    CLAIM_CONFIDENCE_LEVELS = {"multi_source", "single_source", "official_statement"}
    DEFAULT_CLAIM_CONFIDENCE = "single_source"
    VALID_CATEGORIES = {
        "economia",
        "politica",
        "deportes",
        "tecnologia",
        "entretenimiento",
        "policiales",
        "clima",
        "mundo",
        "salud",
        "sociedad",
        "general",
    }
    CATEGORY_ALIASES = {
        "economia y finanzas": "economia",
        "economicas": "economia",
        "economico": "economia",
        "politica nacional": "politica",
        "nacional": "politica",
        "nacionales": "politica",
        "seguridad": "policiales",
        "policial": "policiales",
        "policia": "policiales",
        "crimen": "policiales",
        "futbol": "deportes",
        "deporte": "deportes",
        "tech": "tecnologia",
        "tecnologia e innovacion": "tecnologia",
        "cultura": "entretenimiento",
        "espectaculos": "entretenimiento",
        "tiempo": "clima",
        "meteorologia": "clima",
        "internacional": "mundo",
        "internacionales": "mundo",
        "ciencia": "salud",
    }

    SYSTEM_PROMPT = """Eres un editor de noticias experto en espanol latinoamericano.
Tu tarea es resumir noticias de forma clara, objetiva y concisa.

Cada resumen debe tener:
- Titulo destacado (max 100 caracteres)
- 2-3 oraciones con contexto suficiente: que paso, a quien afecta y por que importa
- Resumen entre 180 y 320 caracteres, maximo 360 caracteres
- Un dato relevante o dato clave, distinto del titulo

Si una noticia incluye "Otras fuentes que cubren el mismo hecho", usa esa
informacion para dar un resumen mas completo y preciso, pero sigue generando
un unico resumen consolidado por noticia, no uno por fuente.

Ademas del resumen, incluye hasta 3 afirmaciones puntuales ("claims") que sean
hechos verificables y concretos (cifras, fechas, decisiones, resultados), no
opiniones. Por cada afirmacion:
- "claim": el hecho en una oracion corta.
- "confidence": "multi_source" si dos o mas de las fuentes listadas confirman
  el mismo dato, "official_statement" si viene de un comunicado o vocero
  oficial, o "single_source" si solo una fuente lo reporta.
- "claim_type": una palabra que describa el tipo (ej. cifra, fecha, decision,
  resultado, declaracion).
- "article_id": el Article ID exacto (el principal o uno de "Otras fuentes")
  de donde sale ese dato especifico. Nunca inventes un ID que no este listado.
- "excerpt": una frase MUY corta (menos de 160 caracteres) tomada de esa
  fuente que respalde la afirmacion, no un parrafo completo.
Si no hay suficiente informacion para una afirmacion confiable, omite "claims"
o dejalo como arreglo vacio: mejor ninguna afirmacion que una inventada.

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
            prompt += f"   Fuente: {source}\n"
            prompt += self._corroborating_articles_block(article)
            prompt += "\n"

        prompt += "\nDevuelve un arreglo JSON con un objeto por noticia:"
        prompt += """
[
  {
    "article_id": 123,
    "title": "Titulo destacado",
    "summary": "Resumen claro en 2-3 oraciones con contexto suficiente",
    "fact": "Dato relevante",
    "category": "politica",
    "source": "Nombre de la fuente",
    "url": "https://...",
    "claims": [
      {
        "claim": "El bono se paga a partir del 15 de marzo",
        "confidence": "multi_source",
        "claim_type": "fecha",
        "article_id": 123,
        "excerpt": "el pago comenzara el 15 de marzo, confirmo el ministerio"
      }
    ]
  }
]"""

        return prompt

    def _corroborating_articles_block(self, article: dict) -> str:
        """Contexto multi-fuente: otros articulos de la misma historia (Fase 1.3).

        Solo titulo/extracto por fuente adicional, para no disparar el tamano
        del prompt cuando una historia tiene muchos articulos. El Article ID de
        cada uno se expone para que las "claims" (Fase 2.2) puedan citar de
        que fuente exacta sale cada dato.
        """

        others = article.get("corroborating_articles")
        if not isinstance(others, list) or not others:
            return ""

        block = "   Otras fuentes que cubren el mismo hecho:\n"
        for other in others[:4]:
            other_title = str(other.get("title") or "").strip()
            if not other_title:
                continue
            other_source = str(other.get("source") or "").strip()
            other_excerpt = str(other.get("description") or other.get("content") or "").strip()
            other_id = other.get("article_id")
            line = "     -"
            if other_id is not None:
                line += f" [Article ID: {other_id}]"
            line += f" {other_title}"
            if other_source:
                line += f" ({other_source})"
            block += line + "\n"
            if other_excerpt:
                block += f"       {self._truncate_content(other_excerpt, 200)}\n"

        return block if block.count("\n") > 1 else ""

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
        data = self._decode_json_candidate(response)
        if data is None:
            data = self._extract_json_array(response)

        if isinstance(data, dict):
            data = data.get("summaries") or data.get("items") or data.get("data")

        return data if isinstance(data, list) else None

    def _decode_json_candidate(self, response: str) -> Any | None:
        for candidate in self._json_candidates(response):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        return None

    def _json_candidates(self, response: str) -> list[str]:
        response = str(response or "").strip()
        if not response:
            return []

        candidates = [response]

        fenced_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", response, flags=re.IGNORECASE)
        candidates.extend(block.strip() for block in fenced_blocks if block.strip())

        candidates.extend(self._balanced_json_snippets(response))
        return candidates

    def _balanced_json_snippets(self, response: str) -> list[str]:
        snippets = []
        for opener, closer in (("[", "]"), ("{", "}")):
            for start, char in enumerate(response):
                if char != opener:
                    continue

                snippet = self._balanced_json_from(response, start, opener, closer)
                if snippet:
                    snippets.append(snippet)

        return snippets

    def _balanced_json_from(
        self,
        response: str,
        start: int,
        opener: str,
        closer: str,
    ) -> str | None:
        depth = 0
        in_string = False
        escaped = False

        for index in range(start, len(response)):
            char = response[index]

            if escaped:
                escaped = False
                continue

            if char == "\\" and in_string:
                escaped = True
                continue

            if char == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return response[start : index + 1]

        return None

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
            title = self._limit_text(
                self._clean_generated_text(original.get("title") or item.get("title") or ""),
                self.TITLE_MAX_CHARS,
            )
            summary = self._summary_with_context(item.get("summary") or "", original)

            if not title or not summary:
                logger.warning(f"Ignoring incomplete summary item at index {index}: {item}")
                continue

            summaries.append(
                {
                    "title": title,
                    "summary": summary,
                    "fact": self._limit_text(
                        self._clean_generated_text(item.get("fact") or ""),
                        self.FACT_MAX_CHARS,
                    ),
                    "category": self._resolve_category(category, item, original),
                    "article_id": item.get("article_id")
                    or original.get("id")
                    or original.get("article_id"),
                    "story_cluster_id": original.get("story_cluster_id"),
                    "source_article_count": self._source_article_count(original),
                    "source": item.get("source") or original.get("source"),
                    "url": item.get("url") or original.get("url"),
                    "claims": self._normalize_claims(item, original),
                }
            )

        return summaries

    def _valid_evidence_articles(self, original: dict) -> dict[int, dict]:
        """Article IDs a los que un claim puede apuntar de verdad: el articulo
        principal y sus fuentes corroborantes (Fase 1.3), cada uno con URL real.
        Nunca un ID inventado por el modelo."""

        valid: dict[int, dict] = {}

        main_id = self._safe_int(original.get("id") or original.get("article_id"))
        main_url = original.get("url")
        if main_id is not None and main_url:
            valid[main_id] = {"url": main_url, "published_at": original.get("published_at")}

        for sibling in original.get("corroborating_articles") or []:
            if not isinstance(sibling, dict):
                continue
            sibling_id = self._safe_int(sibling.get("article_id"))
            sibling_url = sibling.get("url")
            if sibling_id is not None and sibling_url:
                valid[sibling_id] = {
                    "url": sibling_url,
                    "published_at": sibling.get("published_at"),
                }

        return valid

    def _normalize_claims(self, item: dict, original: dict) -> list[dict]:
        """Afirmaciones puntuales con evidencia real (Fase 2.2).

        Descarta cualquier claim sin texto o cuyo article_id no corresponda a
        una fuente real de esta noticia (principal o corroborante) — nunca se
        inserta una URL inventada por el modelo.
        """

        raw_claims = item.get("claims")
        if not isinstance(raw_claims, list) or not raw_claims:
            return []

        valid_articles = self._valid_evidence_articles(original)
        if not valid_articles:
            return []

        fallback_article_id = next(iter(valid_articles))

        claims: list[dict] = []
        for raw in raw_claims:
            if not isinstance(raw, dict):
                continue

            claim_text = self._limit_text(
                self._clean_generated_text(raw.get("claim") or ""), self.CLAIM_MAX_CHARS
            )
            if not claim_text:
                continue

            article_id = self._safe_int(raw.get("article_id"))
            if article_id not in valid_articles:
                article_id = fallback_article_id
            evidence = valid_articles[article_id]

            confidence = str(raw.get("confidence") or "").strip().lower()
            if confidence not in self.CLAIM_CONFIDENCE_LEVELS:
                confidence = self.DEFAULT_CLAIM_CONFIDENCE

            claim_type = self._clean_generated_text(raw.get("claim_type") or "")[:30] or None

            excerpt = self._limit_text(
                self._clean_generated_text(raw.get("excerpt") or ""), self.CLAIM_EXCERPT_MAX_CHARS
            )

            claims.append(
                {
                    "claim": claim_text,
                    "confidence": confidence,
                    "claim_type": claim_type,
                    "article_id": article_id,
                    "source_url": evidence["url"],
                    "source_excerpt": excerpt or None,
                    "published_at": evidence.get("published_at"),
                }
            )
            if len(claims) >= self.CLAIM_MAX_COUNT:
                break

        return claims

    def _safe_int(self, value: Any) -> int | None:
        try:
            if value is None or isinstance(value, bool):
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

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
                        "title": self._limit_text(
                            self._clean_generated_text(subparts[0]),
                            self.TITLE_MAX_CHARS,
                        ),
                        "summary": self._summary_with_context(subparts[1], original)
                        if len(subparts) > 1
                        else "",
                        "fact": self._limit_text(
                            self._clean_generated_text(subparts[2]),
                            self.FACT_MAX_CHARS,
                        )
                        if len(subparts) > 2
                        else "",
                        "category": self._normalize_category(category),
                        "article_id": original.get("id") or original.get("article_id"),
                        "story_cluster_id": original.get("story_cluster_id"),
                        "source_article_count": self._source_article_count(original),
                        "source": original.get("source"),
                        "url": original.get("url"),
                        "claims": [],
                    }
                )

        return summaries

    def _resolve_category(self, category: str, item: dict, original: dict) -> str:
        requested_category = self._valid_category_or_none(category)
        if requested_category:
            return requested_category

        for value in (item.get("category"), original.get("category")):
            normalized = self._valid_category_or_none(value)
            if normalized:
                return normalized

        return "general"

    def _normalize_category(self, value: Any) -> str:
        return self._valid_category_or_none(value) or "general"

    def _valid_category_or_none(self, value: Any) -> str | None:
        normalized = self._normalize_text(value)
        normalized = self.CATEGORY_ALIASES.get(normalized, normalized)
        return normalized if normalized in self.VALID_CATEGORIES else None

    def _clean_generated_text(self, value: Any) -> str:
        text = str(value or "").strip()
        text = re.sub(r"^\s*(?:\d+[\.)]\s*)+", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def _normalize_text(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _summary_with_context(self, value: Any, original: dict) -> str:
        summary = self._clean_generated_text(value)
        if len(summary) >= self.SUMMARY_MIN_CHARS:
            return self._limit_text(summary, self.SUMMARY_MAX_CHARS)

        context = self._clean_generated_text(
            original.get("description") or original.get("excerpt") or original.get("content") or ""
        )
        if not context:
            return self._limit_text(summary, self.SUMMARY_MAX_CHARS)

        combined = summary
        for sentence in self._context_sentences(context):
            if not self._adds_context(combined, sentence):
                continue
            combined = self._append_sentence(combined, sentence)
            if len(combined) >= self.SUMMARY_MIN_CHARS:
                break

        return self._limit_text(combined, self.SUMMARY_MAX_CHARS)

    def _context_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def _append_sentence(self, current: str, sentence: str) -> str:
        if not current:
            return sentence

        separator = " " if current[-1] in ".!?" else ". "
        return f"{current}{separator}{sentence}"

    def _adds_context(self, current: str, sentence: str) -> bool:
        normalized_current = self._clean_generated_text(current).lower()
        normalized_sentence = self._clean_generated_text(sentence).lower()
        if not normalized_sentence:
            return False
        return normalized_sentence not in normalized_current and normalized_current not in normalized_sentence

    def _source_article_count(self, article: dict) -> int:
        sources = article.get("corroborating_sources")
        if isinstance(sources, list) and sources:
            return len({str(source).strip().lower() for source in sources if str(source).strip()})
        return 1

    def _limit_text(self, value: str, max_chars: int) -> str:
        if len(value) <= max_chars:
            return value

        truncated = value[:max_chars].rsplit(" ", 1)[0].strip()
        return truncated or value[:max_chars].strip()
