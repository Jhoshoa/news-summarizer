import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime
from typing import Optional

from loguru import logger


class Deduplicator:
    """Elimina noticias duplicadas usando múltiples estrategias."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold

    def deduplicate(self, news: list[dict]) -> list[dict]:
        """Pipeline completo de deduplicación."""

        unique_by_url = self._deduplicate_by_url(news)
        unique_by_title = self._deduplicate_by_title(unique_by_url)

        logger.info(f"Deduplicación: {len(news)} -> {len(unique_by_title)} noticias")
        return unique_by_title

    def _deduplicate_by_url(self, news: list[dict]) -> list[dict]:
        """Elimina duplicados exactos por URL hash."""

        seen = set()
        unique = []

        for article in news:
            url = article.get("url", "")
            if not url:
                unique.append(article)
                continue

            url_hash = hashlib.md5(url.encode()).hexdigest()
            if url_hash not in seen:
                seen.add(url_hash)
                unique.append(article)

        return unique

    def _deduplicate_by_title(self, news: list[dict]) -> list[dict]:
        """Elimina duplicados por título similar (fuzzy matching)."""

        unique = []
        seen_titles = []

        for article in news:
            title_norm = self._normalize(article.get("title", ""))

            is_duplicate = False
            best_match = None

            for idx, seen in enumerate(seen_titles):
                similarity = SequenceMatcher(None, title_norm, seen).ratio()
                if similarity >= self.threshold:
                    is_duplicate = True
                    if article.get("published_at"):
                        if (
                            not seen_titles[idx].get("_latest_time")
                            or article["published_at"]
                            > seen_titles[idx]["_latest_time"]
                        ):
                            best_match = idx
                    break

            if is_duplicate and best_match is not None:
                seen_titles[best_match] = title_norm
                seen_titles[best_match]["_latest_time"] = article.get("published_at")
                unique[best_match] = article
            elif not is_duplicate:
                unique.append(article)
                seen_titles.append(title_norm)

        return unique

    def _normalize(self, text: str) -> str:
        """Normaliza texto para comparación."""

        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text
