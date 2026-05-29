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
    }
    DEFAULT_FIELD_WEIGHTS = {
        "title": 3.0,
        "description": 2.0,
        "content": 1.0,
        "source_category": 1.5,
    }
    DEFAULT_THRESHOLDS = {
        "min_score": 2.0,
        "accept_margin": 2.0,
        "low_confidence_threshold": 0.62,
    }
    DEFAULT_LIMITS = {"content_chars": 1200}

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
        self.valid_categories = set(self.categories) | {"general"}

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

        category_descriptions = "\n".join(
            f"- {category}: {rules.get('description', '')}"
            for category, rules in self.categories.items()
        )
        prompt = f"""Clasifica esta noticia en UNA sola categoria.

Titulo: {article.get("title")}
Descripcion: {str(article.get("description") or "")[:300]}

Categorias disponibles:
{category_descriptions}
- general: noticia que no encaja claramente en las categorias anteriores.

Responde SOLO JSON valido con esta forma:
{{"category": "politica", "confidence": 0.82, "reason": "motivo breve"}}"""

        try:
            result = await self.llm.chat(prompt, quality="fast")
            parsed = json.loads(result)
            category = self._normalize(parsed.get("category", "general"))
            if category in self.valid_categories:
                article["category_confidence"] = self._safe_float(parsed.get("confidence"), 0.0)
                article["category_reason"] = str(parsed.get("reason") or "llm")
                article["category_method"] = "llm"
                return category

            return "general"

        except Exception as e:
            logger.error(f"Error en clasificacion IA: {e}")
            return self.classify(article)

    def classify_batch(self, news: list[dict]) -> list[dict]:
        """Clasifica una lista de noticias y agrega metadatos auditables."""

        for article in news:
            decision = self.classify_article(article)
            article["category"] = decision.category
            article["category_confidence"] = decision.confidence
            article["category_scores"] = decision.scores
            article["category_reason"] = decision.reason
            article["category_method"] = decision.method

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
        }

    def _fallback_config(self) -> dict[str, Any]:
        return {
            "categories": self.FALLBACK_CATEGORIES,
            "field_weights": self.DEFAULT_FIELD_WEIGHTS,
            "thresholds": self.DEFAULT_THRESHOLDS,
            "limits": self.DEFAULT_LIMITS,
        }

    def _article_fields(self, article: dict) -> dict[str, str]:
        content_limit = int(self.limits["content_chars"])
        return {
            "title": self._normalize(article.get("title", "")),
            "description": self._normalize(article.get("description", "")),
            "content": self._normalize(str(article.get("content") or "")[:content_limit]),
            "source_category": self._normalize(article.get("category", "")),
        }

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
