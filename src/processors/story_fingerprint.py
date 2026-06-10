from __future__ import annotations

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

MAX_EXCERPT_CHARS = 280
TITLE_WEIGHT = 0.65
CONTENT_WEIGHT = 0.35

LOW_VALUE_PREFIXES = (
    "video",
    "ultima hora",
    "ultimo momento",
    "en vivo",
    "envivo",
)


def normalize_story_text(value: Any) -> str:
    """Normaliza texto para comparar historias sin depender de URL o fuente."""

    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()

    previous = None
    while previous != text:
        previous = text
        for prefix in LOW_VALUE_PREFIXES:
            text = re.sub(rf"^{re.escape(prefix)}\s+", "", text).strip()

    return text


def build_canonical_key(article: dict) -> str:
    category = normalize_story_text(article.get("category") or "general")
    title = normalize_story_text(article.get("title"))
    excerpt = _story_excerpt(article)

    parts = [part for part in (category, title, excerpt) if part]
    return " | ".join(parts)[:500]


def build_content_fingerprint(article: dict) -> str:
    canonical_key = build_canonical_key(article)
    return hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()


def story_similarity(a: dict, b: dict) -> float:
    left_title = normalize_story_text(a.get("title"))
    right_title = normalize_story_text(b.get("title"))
    if not left_title or not right_title:
        return 0.0

    if build_content_fingerprint(a) == build_content_fingerprint(b):
        return 1.0

    title_similarity = SequenceMatcher(None, left_title, right_title).ratio()
    content_similarity = _token_jaccard(_story_text(a), _story_text(b))

    if _is_too_short_for_fuzzy_match(a, b) and title_similarity < 0.92:
        return 0.0

    return round((title_similarity * TITLE_WEIGHT) + (content_similarity * CONTENT_WEIGHT), 4)


def _story_excerpt(article: dict) -> str:
    for field in ("content", "description", "excerpt", "summary"):
        value = normalize_story_text(article.get(field))
        if value:
            return value[:MAX_EXCERPT_CHARS]
    return ""


def _story_text(article: dict) -> str:
    return " ".join(
        part
        for part in (
            normalize_story_text(article.get("title")),
            _story_excerpt(article),
        )
        if part
    )


def _token_jaccard(left: str, right: str) -> float:
    left_tokens = _significant_tokens(left)
    right_tokens = _significant_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0

    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _significant_tokens(text: str) -> set[str]:
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
        "noticia",
        "informa",
    }
    return {
        token
        for token in re.findall(r"\w+", text, flags=re.UNICODE)
        if len(token) >= 4 and token not in stopwords
    }


def _is_too_short_for_fuzzy_match(a: dict, b: dict) -> bool:
    left_excerpt = _story_excerpt(a)
    right_excerpt = _story_excerpt(b)
    return len(left_excerpt.split()) < 6 or len(right_excerpt.split()) < 6
