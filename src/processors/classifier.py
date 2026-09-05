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
    # Que tan probable es que esta decision este mal, para priorizar el cupo
    # limitado del fallback de IA (ver classify_batch_async) cuando hay mas
    # articulos "rules_low_confidence" que cupo disponible en la corrida.
    # Un termino marcado `ambiguous: true` que gano la categoria fuerza esto
    # al maximo (10.0); si no, es el mayor entre "un termino domina el
    # score" y "el margen/confianza es bajo". 0.0 en confianza alta y sin
    # dominancia de un solo termino.
    risk_score: float = 0.0


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
        "dominant_term_ratio": 0.5,
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

    def classify_article(self, article: dict) -> ClassificationDecision:
        """Clasifica una noticia y devuelve categoria, confianza y explicacion."""

        field_text = self._article_fields(article)
        scores: dict[str, float] = {}
        reasons: dict[str, list[str]] = {}
        contributions: dict[str, dict[str, float]] = {}
        ambiguous_by_category: dict[str, set[str]] = {}

        for category, rules in self.categories.items():
            score, category_reasons, positive_contributions, ambiguous_terms = self._score_category(
                category, rules, field_text
            )
            scores[category] = round(max(score, 0.0), 4)
            if category_reasons:
                reasons[category] = category_reasons
            contributions[category] = positive_contributions
            ambiguous_by_category[category] = ambiguous_terms

        top_category, top_score = self._top_score(scores)
        second_score = self._second_score(scores, top_category)
        min_score = self.thresholds["min_score"]
        accept_margin = self.thresholds["accept_margin"]
        low_confidence_threshold = self.thresholds["low_confidence_threshold"]
        dominant_term_ratio = self.thresholds.get("dominant_term_ratio", 0.5)

        if top_score < min_score:
            return ClassificationDecision(
                category="general",
                confidence=0.0,
                scores=scores,
                reason="sin_senales_suficientes",
                method="rules",
                risk_score=0.0,
            )

        confidence = self._confidence(top_score, second_score)
        margin = top_score - second_score
        method = "rules"
        if margin < accept_margin or confidence < low_confidence_threshold:
            method = "rules_low_confidence"

        # Amortiguador de termino dominante: si un solo termino explica la
        # mayor parte del score ganador, no confiar en el margen/confianza
        # aunque parezcan altos -- un homonimo bien ubicado (ej. "penal" o
        # "defensa" en un caso judicial) puede ganar solo con score y margen
        # convincentes sin que ninguna otra categoria compita de verdad. Ver
        # docs/mejorar-comportamiento-categorias si existe, o el caso real
        # de /article/4344 (clasificado "deportes" por "defensa"+"penal").
        top_contributions = contributions.get(top_category) or {}
        max_term_ratio = 0.0
        if top_contributions and top_score > 0:
            max_term_ratio = max(top_contributions.values()) / top_score
            if max_term_ratio >= dominant_term_ratio:
                method = "rules_low_confidence"

        # Terminos marcados `ambiguous: true` en el YAML: si alguno participo
        # en el score ganador, forzar revision aunque no domine el score por
        # si solo -- son casos ya identificados como riesgosos que conviene
        # que el fallback de IA revise siempre.
        is_known_ambiguous_term = bool(ambiguous_by_category.get(top_category))
        if is_known_ambiguous_term:
            method = "rules_low_confidence"

        # risk_score prioriza el cupo limitado del fallback de IA
        # (classify_batch_async) cuando hay mas articulos "rules_low_confidence"
        # que cupo en la corrida -- un termino ya identificado como ambiguo
        # (ej. "mundial"/"bolivar") va primero siempre, despues el que mas
        # dependa de un solo termino, despues el margen/confianza mas bajo.
        # Sin esto, el cupo se gastaba por orden de aparicion en la lista y
        # los casos mas riesgosos podian quedarse sin revisar (ver casos
        # reales /article/5097 y /article/5109).
        risk_score = max(max_term_ratio, 1.0 - confidence)
        if is_known_ambiguous_term:
            risk_score = max(risk_score, 10.0)

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
            risk_score=round(risk_score, 4),
        )

    async def classify_batch_async(self, news: list[dict]) -> list[dict]:
        """Clasifica noticias y usa LLM solo para casos ambiguos configurados.

        El cupo de revision con IA (`max_articles_per_batch`) es limitado por
        corrida. Antes se gastaba en el orden en que aparecian los articulos
        en la corrida (primero en llegar, primero en revisarse), asi que un
        articulo realmente riesgoso podia quedarse sin revision solo por mala
        suerte de orden -- paso con los casos reales /article/5097 y
        /article/5109 ("mundial"/"bolivar"), ya marcados `rules_low_confidence`
        pero descartados con `ai_fallback_batch_limit_reached` porque otros
        articulos menos riesgosos agotaron el cupo primero. Por eso se
        clasifica todo con reglas primero, y el cupo de IA se reparte por
        `risk_score` descendente en vez de por orden de aparicion.
        """

        max_ai_articles = int(self.ai_fallback["max_articles_per_batch"])

        eligible: list[tuple[dict, ClassificationDecision]] = []
        for article in news:
            rule_decision = self.classify_article(article)
            self._apply_decision(article, rule_decision)

            if self._should_use_llm(rule_decision):
                eligible.append((article, rule_decision))

        eligible.sort(key=lambda pair: pair[1].risk_score, reverse=True)

        to_review = eligible[:max_ai_articles]
        skipped = eligible[max_ai_articles:]

        if skipped:
            logger.warning(
                "Cupo de fallback de IA agotado: {} articulos elegibles, "
                "{} revisados, {} descartados por cupo (max_articles_per_batch={})",
                len(eligible),
                len(to_review),
                len(skipped),
                max_ai_articles,
            )

        for article, _rule_decision in skipped:
            article["category_llm_error"] = "ai_fallback_batch_limit_reached"

        for article, rule_decision in to_review:
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
    ) -> tuple[float, list[str], dict[str, float], set[str]]:
        """Puntua una categoria contra un articulo.

        Cada termino cuenta una sola vez por categoria, tomando el campo donde
        mejor puntua (no se suma titulo+contenido si el mismo termino aparece
        en ambos) -- evita que una sola palabra repetida infle el score y el
        margen artificialmente. `positive_contributions` (termino -> puntos)
        y `ambiguous_terms` (terminos marcados `ambiguous: true` en el YAML
        que matchearon) alimentan el amortiguador de termino dominante y el
        override de terminos ambiguos en classify_article.
        """

        reasons: list[str] = []
        positive_contributions: dict[str, float] = {}
        ambiguous_terms: set[str] = set()

        for rule in rules.get("positive", []):
            best_value, best_field = self._best_term_match(rule, field_text, self._safe_float(rule.get("weight"), 1.0))
            if best_value <= 0:
                continue
            term = str(rule.get("term") or "").strip()
            positive_contributions[term] = best_value
            reasons.append(f"{best_field}:{term}(+{best_value:g})")
            if rule.get("ambiguous"):
                ambiguous_terms.add(term)

        negative_total = 0.0
        for rule in rules.get("negative", []):
            best_value, best_field = self._best_term_match(rule, field_text, self._safe_float(rule.get("weight"), 1.0))
            if best_value <= 0:
                continue
            term = str(rule.get("term") or "").strip()
            negative_total += best_value
            reasons.append(f"{best_field}:{term}(-{best_value:g})")

        source_text = field_text.get("source_category")
        if source_text and source_text == category:
            field_weight = self.field_weights.get("source_category", 1.0)
            positive_contributions["source_category:categoria_fuente"] = field_weight
            reasons.append(f"source_category:categoria_fuente(+{field_weight:g})")

        score = sum(positive_contributions.values()) - negative_total
        return score, reasons, positive_contributions, ambiguous_terms

    def _best_term_match(
        self,
        rule: dict[str, Any],
        field_text: dict[str, str],
        weight: float,
    ) -> tuple[float, str]:
        """Mejor puntaje de un termino entre campos (titulo/descripcion/contenido).

        No usa el campo 'source_category' aqui: ese se maneja aparte en
        _score_category como bonus de categoria-fuente, no como termino.
        """

        term = str(rule.get("term") or "").strip()
        if not term:
            return 0.0, ""

        is_regex = bool(rule.get("regex"))
        best_value = 0.0
        best_field = ""
        for field, text in field_text.items():
            if field == "source_category" or not text:
                continue
            if not self._matches_rule(text, term, is_regex):
                continue
            value = weight * self.field_weights.get(field, 1.0)
            if value > best_value:
                best_value = value
                best_field = field

        return best_value, best_field

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
