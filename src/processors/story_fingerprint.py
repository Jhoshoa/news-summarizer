from __future__ import annotations

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse

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

# Parametros de tracking que no cambian que articulo es: dos URLs que solo
# difieren en estos deben normalizar al mismo valor.
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = frozenset(
    {
        "fbclid",
        "gclid",
        "gclsrc",
        "dclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
        "igshid",
        "ref_src",
        "ref",
        "yclid",
        "twclid",
        "spm",
        "_ga",
        "mkt_tok",
        "cmpid",
        "amp",
    }
)


def normalize_url(value: Any) -> str:
    """Normaliza una URL para comparar identidad de articulo, no solo bytes iguales.

    Unifica esquema/host, quita parametros de tracking y el fragmento, y
    ordena los parametros restantes para que el orden en que la fuente los
    emite no afecte la comparacion.
    """

    raw = str(value or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw if "://" in raw else f"//{raw}", scheme="https")
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    path = parsed.path.rstrip("/") or ""

    kept_params = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
        and not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    kept_params.sort()
    query = urlencode(kept_params)

    normalized = f"https://{netloc}{path}"
    if query:
        normalized += f"?{query}"
    return normalized


def build_url_fingerprint(value: Any) -> str:
    normalized = normalize_url(value)
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def temporal_proximity_factor(hours_apart: float, *, window_hours: float) -> float:
    """Factor en (floor, 1.0] que penaliza matches cerca del borde de la ventana.

    No aporta nada cuando dos articulos son casi simultaneos (factor ~1.0);
    reduce el score de similitud hasta un 15% cuando la distancia temporal se
    acerca al limite de la ventana de busqueda de historias relacionadas, para
    evitar que temas recurrentes con titulares parecidos (ej. encuestas
    semanales) se agrupen como si fueran la misma historia.
    """

    if window_hours <= 0:
        return 1.0

    floor = 0.85
    ratio = min(abs(hours_apart) / window_hours, 1.0)
    return 1.0 - (1.0 - floor) * ratio


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


UPDATE_TITLE_SIMILARITY_THRESHOLD = 0.92


def is_meaningful_title_update(old_title: str, new_title: str) -> bool:
    """True si un articulo nuevo en una historia existente trae info distinta.

    Se usa para decidir si vale la pena mostrarle al usuario una nota de
    "Actualizacion: ..." (Fase 1.4) o si es solo el mismo hecho republicado
    con el titulo casi identico.
    """

    old_norm = normalize_story_text(old_title)
    new_norm = normalize_story_text(new_title)
    if not old_norm or not new_norm:
        return False

    similarity = SequenceMatcher(None, old_norm, new_norm).ratio()
    return similarity < UPDATE_TITLE_SIMILARITY_THRESHOLD


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
