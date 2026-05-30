from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from difflib import SequenceMatcher
from hashlib import sha1
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from loguru import logger


class NewsRanker:
    """Calcula relevancia editorial con componentes configurables."""

    DEFAULT_CONFIG_PATH = Path("config/scoring.yaml")
    DEFAULT_CONFIG: dict[str, Any] = {
        "scale": {"min": 0, "max": 100},
        "weights": {
            "recency": 0.20,
            "source": 0.15,
            "content_quality": 0.22,
            "impact": 0.25,
            "corroboration": 0.10,
            "category_confidence": 0.10,
        },
        "recency": {
            "buckets": [
                {"max_hours": 1, "score": 100},
                {"max_hours": 3, "score": 90},
                {"max_hours": 6, "score": 75},
                {"max_hours": 12, "score": 60},
                {"max_hours": 24, "score": 45},
                {"max_hours": 48, "score": 25},
            ],
            "default_score": 10,
            "missing_score": 20,
        },
        "sources": {
            "unitel": 82,
            "reduno": 84,
            "radiofides": 84,
            "redbolivision": 78,
            "opinion": 82,
            "el_deber": 84,
            "la_razon": 82,
            "newsapi": 62,
            "default": 55,
        },
        "source_aliases": {
            "red uno": "reduno",
            "radio fides": "radiofides",
            "red bolivision": "redbolivision",
            "el deber": "el_deber",
            "la razon": "la_razon",
        },
        "content_quality": {
            "base_score": 35,
            "min_good_words": 120,
            "min_excellent_words": 300,
            "good_words_bonus": 20,
            "excellent_words_bonus": 10,
            "image_bonus": 10,
            "description_bonus": 10,
            "title_bonus": 10,
            "max_score": 100,
        },
        "impact_terms": {
            "high": {
                "score": 100,
                "terms": [
                    "bloqueo nacional",
                    "estado de emergencia",
                    "banco central",
                    "crisis",
                    "muertos",
                    "fallecidos",
                    "dolar",
                    "elecciones",
                    "combustible",
                    "bloqueo indefinido",
                    "escasez de combustible",
                    "tipo de cambio",
                    "riesgo pais",
                    "conflicto social",
                    "transporte pesado",
                    "medidas de presion",
                ],
            },
            "medium": {
                "score": 70,
                "terms": [
                    "bloqueo",
                    "paro",
                    "protesta",
                    "inflacion",
                    "deuda",
                    "exportacion",
                    "ley",
                    "candidato",
                    "gobierno",
                    "seguridad",
                ],
            },
            "low": {
                "score": 35,
                "terms": ["anuncio", "reunion", "informe", "operativo", "campana"],
            },
        },
        "corroboration": {
            "same_story_title_similarity": 0.82,
            "same_story_token_jaccard": 0.55,
            "min_token_length": 4,
            "multi_source_bonus": {
                "two_sources": 70,
                "three_or_more_sources": 100,
            },
            "default_score": 0,
        },
        "category_confidence": {
            "missing_score": 45,
            "buckets": [
                {"min": 0.80, "score": 100},
                {"min": 0.60, "score": 75},
                {"min": 0.40, "score": 55},
            ],
            "default_score": 35,
        },
        "penalties": {
            "missing_content": 25,
            "short_content": 15,
            "duplicated_description_content": 20,
            "missing_date": 10,
            "unknown_source": 8,
            "low_category_confidence": 10,
        },
    }

    def __init__(
        self,
        weights: dict | None = None,
        config_path: str | Path | None = None,
    ):
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.config = self._load_config(self.config_path)
        if weights:
            self.config["weights"] = {**self.config["weights"], **weights}

        self.weights: dict[str, float] = {
            key: self._safe_float(value, 0.0)
            for key, value in self.config["weights"].items()
        }
        self.scale_min = self._safe_float(self.config["scale"].get("min"), 0.0)
        self.scale_max = self._safe_float(self.config["scale"].get("max"), 100.0)
        self.sources = {
            self._normalize_source(source): self._safe_float(score, 55.0)
            for source, score in self.config["sources"].items()
        }
        self.source_aliases = {
            self._normalize_source(alias): self._normalize_source(target)
            for alias, target in self.config["source_aliases"].items()
        }

    def rank(self, news: list[dict], limit: int | None = None) -> list[dict]:
        self._annotate_corroboration(news)

        for item in news:
            score, components, reasons = self._calculate_score_details(item)
            item["score"] = score
            item["score_components"] = components
            item["score_reason"] = "; ".join(reasons)

        ranked = sorted(news, key=lambda item: item.get("score", 0), reverse=True)
        return ranked[:limit] if limit else ranked

    def _calculate_score(self, item: dict) -> float:
        score, _, _ = self._calculate_score_details(item)
        return score

    def _calculate_score_details(self, item: dict) -> tuple[float, dict[str, float], list[str]]:
        reasons: list[str] = []
        components = {
            "recency": self._recency_score(item.get("published_at"), reasons),
            "source": self._source_score(item.get("source"), reasons),
            "content_quality": self._content_quality_score(item, reasons),
            "impact": self._impact_score(item, reasons),
            "corroboration": self._corroboration_score(item, reasons),
            "category_confidence": self._category_confidence_score(
                item.get("category_confidence"),
                reasons,
            ),
        }
        penalties = self._penalty_score(item, reasons)

        weighted_score = sum(
            components[name] * self.weights.get(name, 0.0) for name in components
        )
        final_score = self._clamp(weighted_score - penalties, self.scale_min, self.scale_max)
        components["penalties"] = round(penalties, 2)

        return round(final_score, 2), {key: round(value, 2) for key, value in components.items()}, reasons

    def _recency_score(self, published_at: Any, reasons: list[str]) -> float:
        recency_config = self.config["recency"]
        if not isinstance(published_at, datetime):
            reasons.append("fecha ausente")
            return self._safe_float(recency_config.get("missing_score"), 20.0)

        now = datetime.now(UTC) if published_at.tzinfo else datetime.now()
        hours_old = max((now - published_at).total_seconds() / 3600, 0)
        for bucket in recency_config.get("buckets", []):
            max_hours = self._safe_float(bucket.get("max_hours"), 0.0)
            if hours_old < max_hours:
                score = self._safe_float(bucket.get("score"), 0.0)
                reasons.append(f"recencia<{max_hours:g}h")
                return score

        reasons.append("recencia baja")
        return self._safe_float(recency_config.get("default_score"), 10.0)

    def _source_score(self, source: Any, reasons: list[str]) -> float:
        normalized_source = self._canonical_source(source)
        if not normalized_source:
            reasons.append("fuente ausente")
            return self._safe_float(self.sources.get("default"), 55.0)

        if normalized_source not in self.sources:
            reasons.append(f"fuente desconocida:{normalized_source}")
            return self._safe_float(self.sources.get("default"), 55.0)

        reasons.append(f"fuente:{normalized_source}")
        return self.sources[normalized_source]

    def _content_quality_score(self, item: dict, reasons: list[str]) -> float:
        config = self.config["content_quality"]
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        content = str(item.get("content") or "").strip()
        word_count = self._word_count(content)
        score = self._safe_float(config.get("base_score"), 35.0)

        if word_count >= int(config.get("min_good_words", 120)):
            score += self._safe_float(config.get("good_words_bonus"), 20.0)
            reasons.append("contenido util")
        if word_count >= int(config.get("min_excellent_words", 300)):
            score += self._safe_float(config.get("excellent_words_bonus"), 10.0)
            reasons.append("contenido completo")
        if item.get("image"):
            score += self._safe_float(config.get("image_bonus"), 10.0)
            reasons.append("con imagen")
        if 60 <= len(description) <= 280:
            score += self._safe_float(config.get("description_bonus"), 10.0)
            reasons.append("descripcion util")
        if 30 <= len(title) <= 140:
            score += self._safe_float(config.get("title_bonus"), 10.0)
            reasons.append("titulo informativo")

        max_score = self._safe_float(config.get("max_score"), 100.0)
        return self._clamp(score, self.scale_min, max_score)

    def _impact_score(self, item: dict, reasons: list[str]) -> float:
        text = self._normalize_text(
            " ".join(
                [
                    str(item.get("title") or ""),
                    str(item.get("description") or ""),
                    str(item.get("content") or "")[:2000],
                ]
            )
        )

        best_score = 0.0
        best_term = ""
        best_level = ""
        for level, level_config in self.config["impact_terms"].items():
            level_score = self._safe_float(level_config.get("score"), 0.0)
            for term in level_config.get("terms", []):
                normalized_term = self._normalize_text(term)
                if self._contains_term(text, normalized_term) and level_score > best_score:
                    best_score = level_score
                    best_term = normalized_term
                    best_level = str(level)

        if best_term:
            reasons.append(f"impacto {best_level}:{best_term}")
        else:
            reasons.append("impacto bajo")
        return best_score

    def _category_confidence_score(self, confidence: Any, reasons: list[str]) -> float:
        config = self.config["category_confidence"]
        if confidence is None:
            reasons.append("confianza categoria ausente")
            return self._safe_float(config.get("missing_score"), 45.0)

        value = self._safe_float(confidence, 0.0)
        for bucket in config.get("buckets", []):
            minimum = self._safe_float(bucket.get("min"), 0.0)
            if value >= minimum:
                score = self._safe_float(bucket.get("score"), 0.0)
                reasons.append(f"categoria confianza>={minimum:g}")
                return score

        reasons.append("categoria baja confianza")
        return self._safe_float(config.get("default_score"), 35.0)

    def _penalty_score(self, item: dict, reasons: list[str]) -> float:
        penalties = self.config["penalties"]
        description = str(item.get("description") or "").strip()
        content = str(item.get("content") or "").strip()
        penalty = 0.0

        if not content:
            penalty += self._safe_float(penalties.get("missing_content"), 25.0)
            reasons.append("penalizacion:sin contenido")
        elif self._word_count(content) < 60:
            penalty += self._safe_float(penalties.get("short_content"), 15.0)
            reasons.append("penalizacion:contenido corto")

        if description and content and self._normalize_text(description) == self._normalize_text(content):
            penalty += self._safe_float(penalties.get("duplicated_description_content"), 20.0)
            reasons.append("penalizacion:descripcion duplicada")

        if not isinstance(item.get("published_at"), datetime):
            penalty += self._safe_float(penalties.get("missing_date"), 10.0)

        if self._canonical_source(item.get("source")) not in self.sources:
            penalty += self._safe_float(penalties.get("unknown_source"), 8.0)

        confidence = item.get("category_confidence")
        if confidence is not None and self._safe_float(confidence, 0.0) < 0.4:
            penalty += self._safe_float(penalties.get("low_category_confidence"), 10.0)
            reasons.append("penalizacion:categoria baja confianza")

        return penalty

    def _annotate_corroboration(self, news: list[dict]) -> None:
        clusters: list[list[dict]] = []

        for article in news:
            article.pop("cluster_id", None)
            article["corroborating_sources"] = [self._canonical_source(article.get("source"))]

            matched_cluster = self._find_matching_cluster(article, clusters)
            if matched_cluster is None:
                clusters.append([article])
            else:
                matched_cluster.append(article)

        for cluster in clusters:
            representative = self._cluster_representative(cluster)
            cluster_id = self._cluster_id(representative)
            sources = sorted(
                {
                    source
                    for article in cluster
                    if (source := self._canonical_source(article.get("source")))
                }
            )

            for article in cluster:
                article["cluster_id"] = cluster_id
                article["corroborating_sources"] = sources

    def _find_matching_cluster(
        self,
        article: dict,
        clusters: list[list[dict]],
    ) -> list[dict] | None:
        for cluster in clusters:
            if any(self._same_story(article, candidate) for candidate in cluster):
                return cluster
        return None

    def _same_story(self, left: dict, right: dict) -> bool:
        left_category = str(left.get("category") or "").strip().lower()
        right_category = str(right.get("category") or "").strip().lower()
        if left_category and right_category and left_category != right_category:
            return False

        title_similarity = SequenceMatcher(
            None,
            self._normalize_text(left.get("title")),
            self._normalize_text(right.get("title")),
        ).ratio()
        if title_similarity >= self._corroboration_threshold("same_story_title_similarity", 0.82):
            return True

        token_jaccard = self._token_jaccard(self._story_text(left), self._story_text(right))
        return token_jaccard >= self._corroboration_threshold("same_story_token_jaccard", 0.55)

    def _story_text(self, article: dict) -> str:
        return self._normalize_text(
            " ".join(
                [
                    str(article.get("title") or ""),
                    str(article.get("description") or ""),
                    str(article.get("content") or "")[:600],
                ]
            )
        )

    def _token_jaccard(self, left: str, right: str) -> float:
        left_tokens = self._significant_tokens(left)
        right_tokens = self._significant_tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0

        intersection = left_tokens & right_tokens
        union = left_tokens | right_tokens
        return len(intersection) / len(union)

    def _significant_tokens(self, text: str) -> set[str]:
        min_length = int(self.config["corroboration"].get("min_token_length", 4))
        stopwords = {
            "para",
            "como",
            "esta",
            "este",
            "esto",
            "desde",
            "sobre",
            "entre",
            "tras",
            "ante",
            "bolivia",
        }
        return {
            token
            for token in re.findall(r"\w+", text, flags=re.UNICODE)
            if len(token) >= min_length and token not in stopwords
        }

    def _cluster_representative(self, cluster: list[dict]) -> dict:
        return max(cluster, key=lambda article: self._word_count(str(article.get("title") or "")))

    def _cluster_id(self, article: dict) -> str:
        normalized_title = self._normalize_text(article.get("title"))
        digest = sha1(normalized_title.encode("utf-8")).hexdigest()[:12]
        return f"story-{digest}"

    def _corroboration_score(self, item: dict, reasons: list[str]) -> float:
        config = self.config["corroboration"]
        sources = {
            self._canonical_source(source)
            for source in item.get("corroborating_sources", [])
            if self._canonical_source(source)
        }

        source_count = len(sources)
        if source_count >= 3:
            reasons.append(f"corroborada:{source_count} fuentes")
            return self._safe_float(
                config.get("multi_source_bonus", {}).get("three_or_more_sources"),
                100.0,
            )
        if source_count == 2:
            reasons.append("corroborada:2 fuentes")
            return self._safe_float(
                config.get("multi_source_bonus", {}).get("two_sources"),
                70.0,
            )

        reasons.append("sin corroboracion multi-fuente")
        return self._safe_float(config.get("default_score"), 0.0)

    def _corroboration_threshold(self, name: str, default: float) -> float:
        return self._safe_float(self.config["corroboration"].get(name), default)

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        config = self._deep_copy_config(self.DEFAULT_CONFIG)
        if not config_path.exists():
            logger.warning(f"No existe {config_path}; usando configuracion fallback de scoring")
            return config

        with config_path.open("r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file) or {}

        return self._merge_config(config, loaded)

    def _merge_config(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._merge_config(base[key], value)
            elif value is not None:
                base[key] = value
        return base

    def _deep_copy_config(self, value: dict[str, Any]) -> dict[str, Any]:
        copied: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, dict):
                copied[key] = self._deep_copy_config(item)
            elif isinstance(item, list):
                copied[key] = [entry.copy() if isinstance(entry, dict) else entry for entry in item]
            else:
                copied[key] = item
        return copied

    def _canonical_source(self, source: Any) -> str:
        normalized = self._normalize_source(source)
        return self.source_aliases.get(normalized, normalized)

    def _normalize_source(self, source: Any) -> str:
        normalized = self._normalize_text(source)
        return normalized.replace(" ", "_")

    def _normalize_text(self, text: Any) -> str:
        normalized = unicodedata.normalize("NFD", str(text or "").lower())
        normalized = "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )
        return re.sub(r"\s+", " ", normalized).strip()

    def _contains_term(self, text: str, term: str) -> bool:
        if not term:
            return False
        pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
        return re.search(pattern, text) is not None

    def _word_count(self, text: str) -> int:
        return len(re.findall(r"\w+", text, flags=re.UNICODE))

    def _clamp(self, value: float, min_value: float, max_value: float) -> float:
        return min(max(value, min_value), max_value)

    def _safe_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
