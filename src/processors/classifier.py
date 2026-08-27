from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from loguru import logger


@dataclass(frozen=True)
class ClassificationDecision:
    category: str
    confidence: float
    scores: dict[str, float]
    reason: str
    method: str


class NewsClassifier:
    """Clasifica noticias con reglas ponderadas configurables."""

    DEFAULT_CONFIG_PATH = Path("config/classification.yaml")
    FALLBACK_CATEGORIES = {
        "economia": {
            "description": "Economia, finanzas y mercados.",
            "positive": [{"term": "dolar", "weight": 3}, {"term": "banco", "weight": 2}],
            "negative": [],
        },
        "politica": {
            "description": "Gobierno, elecciones y autoridades.",
            "positive": [{"term": "gobierno", "weight": 2}, {"term": "presidente", "weight": 3}],
            "negative": [{"term": "partido de futbol", "weight": 5}],
        },
        "deportes": {
            "description": "Deportes, futbol y torneos.",
            "positive": [{"term": "futbol", "weight": 4}, {"term": "gol", "weight": 3}],
            "negative": [{"term": "partido politico", "weight": 5}],
        },
        "tecnologia": {
            "description": "Tecnologia, software e internet.",
            "positive": [{"term": "tecnologia", "weight": 3}, {"term": r"\bia\b", "weight": 3, "regex": True}],
            "negative": [],
        },
        "entretenimiento": {
            "description": "Cultura, musica y espectaculos.",
            "positive": [{"term": "cine", "weight": 3}, {"term": "musica", "weight": 3}],
            "negative": [],
        },
        "policiales": {
            "description": "Delitos, crimen, violencia y seguridad ciudadana.",
            "positive": [{"term": "policia", "weight": 3}, {"term": "robo", "weight": 3}],
            "negative": [],
        },
        "clima": {
            "description": "Clima, fenomenos meteorologicos y desastres naturales.",
            "positive": [{"term": "nevada", "weight": 3}, {"term": "terremoto", "weight": 4}],
            "negative": [],
        },
        "mundo": {
            "description": "Noticias internacionales fuera de Bolivia.",
            "positive": [{"term": "casa blanca", "weight": 3}, {"term": "naciones unidas", "weight": 3}],
            "negative": [],
        },
        "salud": {
            "description": "Salud, medicina y ciencia.",
            "positive": [{"term": "hospital", "weight": 3}, {"term": "vacuna", "weight": 3}],
            "negative": [],
        },
        "sociedad": {
            "description": "Vida cotidiana, servicios publicos y temas comunitarios.",
            "positive": [{"term": "defensoria del pueblo", "weight": 3}, {"term": "tramite", "weight": 2}],
            "negative": [],
        },
    }
    DEFAULT_FIELD_WEIGHTS = {
        "title": 3.0,
        "description": 2.0,
        "content": 1.0,
        "source_category": 2.5,
    }
    DEFAULT_THRESHOLDS = {
        "min_score": 2.0,
        "accept_margin": 2.0,
        "low_confidence_threshold": 0.62,
    }
    DEFAULT_LIMITS = {"content_chars": 1200}
    DEFAULT_SOURCE_CATEGORY_MAPPINGS = {"global": {}}
    DEFAULT_AI_FALLBACK = {
        "enabled": False,
        "eligible_methods": ["rules_low_confidence"],
        "quality": "fast",
        "temperature": 0.1,
        "max_tokens": 300,
        "min_confidence": 0.55,
        "max_articles_per_batch": 12,
    }

    def __init__(
        self,
        llm_provider: Any = None,
        config_path: str | Path | None = None,
    ):
        self.llm = llm_provider
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.config = self._load_config(self.config_path)
        self.categories: dict[str, dict[str, Any]] = self.config["categories"]
        self.field_weights: dict[str, float] = self.config["field_weights"]
        self.thresholds: dict[str, float] = self.config["thresholds"]
        self.limits: dict[str, int] = self.config["limits"]
        self.source_category_mappings: dict[str, dict[str, str]] = self.config[
            "source_category_mappings"
        ]
        self.ai_fallback: dict[str, Any] = self.config["ai_fallback"]
        self.valid_categories = set(self.categories) | {"general"}
        self._warn_category_mismatch()

    def _warn_category_mismatch(self) -> None:
        """Compara las categorias cargadas contra DEFAULT_CATEGORIES (fuente de verdad).

        Solo registra un warning: un desajuste no debe tumbar el arranque, pero debe
        quedar visible en logs/Sentry en vez de fallar en silencio como paso con
        "policiales" (ver docs/mejorar-comportamiento-categorias/plan-categorias.md).

        Import diferido (no al tope del modulo) para evitar un ciclo de imports: el
        paquete src.processors ya se importa desde src.db.repository.
        """

        from src.db.repository import DEFAULT_CATEGORIES

        known_categories = set(DEFAULT_CATEGORIES) - {"general"}
        classifier_categories = set(self.categories)

        missing_rules = sorted(known_categories - classifier_categories)
        if missing_rules:
            logger.warning(
                "Categorias sin reglas de clasificacion en {}: {}. Nunca se les asignara "
                "ninguna nota hasta que se agreguen sus reglas.",
                self.config_path,
                ", ".join(missing_rules),
            )

        unknown_categories = sorted(classifier_categories - known_categories)
        if unknown_categories:
            logger.warning(
                "Categorias con reglas de clasificacion en {} pero no registradas en "
                "DEFAULT_CATEGORIES: {}. No apareceran en la suscripcion ni en el frontend.",
                self.config_path,
                ", ".join(unknown_categories),
            )

    def classify(self, article: dict) -> str:
        """Devuelve solo la categoria para mantener compatibilidad."""

        return self.classify_article(article).category

    def classify_article(self, article: dict) -> ClassificationDecision:
        """Clasifica una noticia y devuelve categoria, confianza y explicacion."""

        field_text = self._article_fields(article)
        scores: dict[str, float] = {}
        reasons: dict[str, list[str]] = {}

        for category, rules in self.categories.items():
            score, category_reasons = self._score_category(category, rules, field_text)
            scores[category] = round(max(score, 0.0), 4)
            if category_reasons:
                reasons[category] = category_reasons

        top_category, top_score = self._top_score(scores)
        second_score = self._second_score(scores, top_category)
        min_score = self.thresholds["min_score"]
        accept_margin = self.thresholds["accept_margin"]
        low_confidence_threshold = self.thresholds["low_confidence_threshold"]

        if top_score < min_score:
            return ClassificationDecision(
                category="general",
                confidence=0.0,
                scores=scores,
                reason="sin_senales_suficientes",
                method="rules",
            )

        confidence = self._confidence(top_score, second_score)
        margin = top_score - second_score
        method = "rules"
        if margin < accept_margin or confidence < low_confidence_threshold:
            method = "rules_low_confidence"

        reason = self._build_reason(top_category, reasons.get(top_category, []), top_score, margin)
        logger.debug(
            "Clasificado como '{}' confidence={:.2f}: {}",
            top_category,
            confidence,
            article.get("title", "")[:70],
        )

        return ClassificationDecision(
            category=top_category,
            confidence=round(confidence, 4),
            scores=scores,
            reason=reason,
            method=method,
        )

    async def classify_with_ai(self, article: dict) -> str:
        """Clasifica con IA cuando se invoque explicitamente."""

        if not self.llm:
            return self.classify(article)

        decision = self.classify_article(article)
        llm_decision = await self._classify_with_llm(article, decision)
        if not llm_decision:
            return decision.category

        article["category_confidence"] = llm_decision.confidence
        article["category_reason"] = llm_decision.reason
        article["category_method"] = llm_decision.method
        return llm_decision.category

    def classify_batch(self, news: list[dict]) -> list[dict]:
        """Clasifica una lista de noticias y agrega metadatos auditables."""

        for article in news:
            decision = self.classify_article(article)
            self._apply_decision(article, decision)

        return news

    async def classify_batch_async(self, news: list[dict]) -> list[dict]:
        """Clasifica noticias y usa LLM solo para casos ambiguos configurados."""

        eligible_count = 0
        max_ai_articles = int(self.ai_fallback["max_articles_per_batch"])

        for article in news:
            rule_decision = self.classify_article(article)
            self._apply_decision(article, rule_decision)

            if not self._should_use_llm(rule_decision):
                continue
            if eligible_count >= max_ai_articles:
                article["category_llm_error"] = "ai_fallback_batch_limit_reached"
                continue

            eligible_count += 1
            llm_decision = await self._classify_with_llm(article, rule_decision)
            if llm_decision:
                self._apply_llm_decision(article, llm_decision, rule_decision)

        return news

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        if not config_path.exists():
            logger.warning(f"No existe {config_path}; usando configuracion fallback")
            return self._fallback_config()

        with config_path.open("r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file) or {}

        return {
            "categories": loaded.get("categories") or self.FALLBACK_CATEGORIES,
            "field_weights": {
                **self.DEFAULT_FIELD_WEIGHTS,
                **(loaded.get("field_weights") or {}),
            },
            "thresholds": {
                **self.DEFAULT_THRESHOLDS,
                **(loaded.get("thresholds") or {}),
            },
            "limits": {
                **self.DEFAULT_LIMITS,
                **(loaded.get("limits") or {}),
            },
            "source_category_mappings": self._normalize_source_category_mappings(
                loaded.get("source_category_mappings") or self.DEFAULT_SOURCE_CATEGORY_MAPPINGS
            ),
            "ai_fallback": {
                **self.DEFAULT_AI_FALLBACK,
                **(loaded.get("ai_fallback") or {}),
            },
        }

    def _fallback_config(self) -> dict[str, Any]:
        return {
            "categories": self.FALLBACK_CATEGORIES,
            "field_weights": self.DEFAULT_FIELD_WEIGHTS,
            "thresholds": self.DEFAULT_THRESHOLDS,
            "limits": self.DEFAULT_LIMITS,
            "source_category_mappings": self.DEFAULT_SOURCE_CATEGORY_MAPPINGS,
            "ai_fallback": self.DEFAULT_AI_FALLBACK,
        }

    def _apply_decision(self, article: dict, decision: ClassificationDecision) -> None:
        article["category"] = decision.category
        article["category_confidence"] = decision.confidence
        article["category_scores"] = decision.scores
        article["category_reason"] = decision.reason
        article["category_method"] = decision.method

        raw_source_category = article.get("source_category_raw")
        mapped_source_category = article.pop(
            "_source_category_mapped",
            article.get("source_category_mapped"),
        )
        if raw_source_category:
            article["source_category_raw"] = raw_source_category
        if mapped_source_category:
            article["source_category_mapped"] = mapped_source_category

    def _apply_llm_decision(
        self,
        article: dict,
        llm_decision: ClassificationDecision,
        rule_decision: ClassificationDecision,
    ) -> None:
        article["category_rule_category"] = rule_decision.category
        article["category_rule_confidence"] = rule_decision.confidence
        article["category_rule_reason"] = rule_decision.reason
        self._apply_decision(article, llm_decision)

    def _should_use_llm(self, decision: ClassificationDecision) -> bool:
        if not self.llm or not bool(self.ai_fallback["enabled"]):
            return False

        eligible_methods = {
            str(method) for method in self.ai_fallback.get("eligible_methods", [])
        }
        return decision.method in eligible_methods

    async def _classify_with_llm(
        self,
        article: dict,
        rule_decision: ClassificationDecision,
    ) -> ClassificationDecision | None:
        prompt = self._build_llm_prompt(article, rule_decision)
        quality = str(self.ai_fallback["quality"])
        temperature = self._safe_float(self.ai_fallback["temperature"], 0.1)
        max_tokens = int(self.ai_fallback["max_tokens"])

        try:
            result = await self.llm.chat(
                prompt,
                quality=quality,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            parsed = self._parse_llm_json(result)
            category = self._normalize(parsed.get("category", ""))
            confidence = self._safe_float(parsed.get("confidence"), 0.0)
            reason = str(parsed.get("reason") or "llm_fallback").strip()

            if category not in self.valid_categories:
                article["category_llm_error"] = f"invalid_category:{category or 'empty'}"
                return None

            if confidence < self._safe_float(self.ai_fallback["min_confidence"], 0.55):
                article["category_llm_error"] = f"low_confidence:{confidence:g}"
                return None

            return ClassificationDecision(
                category=category,
                confidence=round(confidence, 4),
                scores=rule_decision.scores,
                reason=f"llm:{reason}",
                method="llm_fallback",
            )
        except Exception as e:
            logger.warning(f"Fallback IA de clasificacion fallo: {e}")
            article["category_llm_error"] = str(e)
            return None

    def _build_llm_prompt(
        self,
        article: dict,
        rule_decision: ClassificationDecision,
    ) -> str:
        category_descriptions = "\n".join(
            f"- {category}: {rules.get('description', '')}"
            for category, rules in self.categories.items()
        )
        content_limit = min(int(self.limits["content_chars"]), 900)
        content = str(article.get("content") or "")[:content_limit]
        scores = json.dumps(rule_decision.scores, ensure_ascii=False, sort_keys=True)

        return f"""Clasifica esta noticia boliviana en UNA sola categoria.

Categorias disponibles:
{category_descriptions}
- general: noticia que no encaja claramente en las categorias anteriores.

Decision por reglas:
- categoria: {rule_decision.category}
- confianza: {rule_decision.confidence}
- scores: {scores}
- razon: {rule_decision.reason}

Noticia:
Titulo: {article.get("title")}
Descripcion: {str(article.get("description") or "")[:400]}
Contenido: {content}

Reglas:
- Responde solo una categoria permitida.
- Usa "general" si no hay una categoria clara.
- Devuelve SOLO JSON valido, sin markdown.

Formato:
{{"category": "politica", "confidence": 0.82, "reason": "motivo breve"}}"""

    def _parse_llm_json(self, response: str) -> dict[str, Any]:
        text = str(response or "").strip()
        if not text:
            raise ValueError("empty_llm_response")

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise
            parsed = json.loads(match.group(0))

        if not isinstance(parsed, dict):
            raise ValueError("llm_response_is_not_object")

        return parsed

    def _article_fields(self, article: dict) -> dict[str, str]:
        content_limit = int(self.limits["content_chars"])
        raw_source_category = self._normalize(article.get("category", ""))
        mapped_source_category = self._map_source_category(
            source=article.get("source", ""),
            raw_category=raw_source_category,
        )
        if raw_source_category:
            article["source_category_raw"] = raw_source_category
        if mapped_source_category:
            article["_source_category_mapped"] = mapped_source_category

        return {
            "title": self._normalize(article.get("title", "")),
            "description": self._normalize(article.get("description", "")),
            "content": self._normalize(str(article.get("content") or "")[:content_limit]),
            "source_category": mapped_source_category or raw_source_category,
        }

    def _normalize_source_category_mappings(
        self,
        mappings: dict[str, Any],
    ) -> dict[str, dict[str, str]]:
        normalized: dict[str, dict[str, str]] = {}

        for source, source_mappings in mappings.items():
            if not isinstance(source_mappings, dict):
                continue

            normalized_source = self._normalize(source)
            normalized[normalized_source] = {}
            for raw_category, mapped_category in source_mappings.items():
                normalized_category = self._normalize(raw_category)
                normalized_target = self._normalize(mapped_category)
                normalized[normalized_source][normalized_category] = normalized_target

        return normalized

    def _map_source_category(self, source: object, raw_category: str) -> str:
        if not raw_category:
            return ""

        normalized_source = self._normalize(source)
        source_mapping = self.source_category_mappings.get(normalized_source, {})
        mapped = source_mapping.get(raw_category)
        if mapped and mapped in self.valid_categories:
            return mapped

        global_mapping = self.source_category_mappings.get("global", {})
        mapped = global_mapping.get(raw_category)
        if mapped and mapped in self.valid_categories:
            return mapped

        return raw_category if raw_category in self.valid_categories else ""

    def _score_category(
        self,
        category: str,
        rules: dict[str, Any],
        field_text: dict[str, str],
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        for field, text in field_text.items():
            if not text:
                continue

            field_weight = self.field_weights.get(field, 1.0)
            if field == "source_category":
                if text == category:
                    score += field_weight
                    reasons.append(f"{field}:categoria_fuente(+{field_weight:g})")
                continue

            positive_score, positive_reasons = self._score_rules(
                rules.get("positive", []),
                text,
                field,
                field_weight,
                positive=True,
            )
            negative_score, negative_reasons = self._score_rules(
                rules.get("negative", []),
                text,
                field,
                field_weight,
                positive=False,
            )
            score += positive_score - negative_score
            reasons.extend(positive_reasons)
            reasons.extend(negative_reasons)

        return score, reasons

    def _score_rules(
        self,
        rules: list[dict[str, Any]],
        text: str,
        field: str,
        field_weight: float,
        *,
        positive: bool,
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        sign = "+" if positive else "-"

        for rule in rules:
            term = str(rule.get("term") or "").strip()
            if not term:
                continue

            if not self._matches_rule(text, term, bool(rule.get("regex"))):
                continue

            value = self._safe_float(rule.get("weight"), 1.0) * field_weight
            score += value
            reasons.append(f"{field}:{term}({sign}{value:g})")

        return score, reasons

    def _matches_rule(self, text: str, term: str, is_regex: bool) -> bool:
        if is_regex:
            try:
                return re.search(term, text, flags=re.IGNORECASE) is not None
            except re.error:
                logger.warning(f"Regex invalida en clasificacion: {term}")
                return False

        normalized_term = self._normalize(term)
        pattern = rf"(?<!\w){re.escape(normalized_term)}(?!\w)"
        return re.search(pattern, text) is not None

    def _top_score(self, scores: dict[str, float]) -> tuple[str, float]:
        if not scores:
            return "general", 0.0
        category = max(scores, key=lambda item: scores[item])
        return category, scores[category]

    def _second_score(self, scores: dict[str, float], top_category: str) -> float:
        remaining = [score for category, score in scores.items() if category != top_category]
        return max(remaining) if remaining else 0.0

    def _confidence(self, top_score: float, second_score: float) -> float:
        return top_score / (top_score + second_score + 1)

    def _build_reason(
        self,
        category: str,
        reasons: list[str],
        top_score: float,
        margin: float,
    ) -> str:
        reason = ";".join(reasons[:8]) if reasons else "sin_detalle"
        return f"{category}:score={top_score:g};margin={margin:g};{reason}"

    def _normalize(self, text: object) -> str:
        normalized = unicodedata.normalize("NFD", str(text or "").lower())
        normalized = "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )
        return re.sub(r"\s+", " ", normalized).strip()

    def _safe_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
