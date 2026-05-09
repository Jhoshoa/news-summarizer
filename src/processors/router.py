from datetime import datetime

from loguru import logger


class NewsRanker:
    """Ranking de noticias por relevancia."""

    SOURCE_WEIGHTS = {
        "radiofides": 1.0,
        "unitel": 1.0,
        "reduno": 1.0,
        "redbolivision": 1.0,
        "lostiempos": 0.95,
        "eldeber": 0.95,
        "newsapi": 0.7,
    }

    URGENT_KEYWORDS = [
        "urgente",
        "importante",
        "rompe",
        "exclusiva",
        "breaking",
        "accidente",
        "tragedia",
        "muerte",
        "fallece",
        "golpe",
        "crisis",
        "emergencia",
        "alerta",
    ]

    def rank(self, news: list[dict], limit: int = 20) -> list[dict]:
        """Ordena noticias por score de relevancia."""

        scored = []

        for article in news:
            score = self._calculate_score(article)
            scored.append((score, article))

        scored.sort(key=lambda x: x[0], reverse=True)

        ranked = [article for score, article in scored[:limit]]

        logger.info(f"Rankeadas {len(news)} -> top {len(ranked)} noticias")
        return ranked

    def _calculate_score(self, article: dict) -> float:
        """Calcula score de relevancia para una noticia."""

        score = 0.0

        recency_score = self._get_recency_score(article)
        score += recency_score * 40

        source_score = self._get_source_score(article)
        score += source_score * 30

        content_score = self._get_content_score(article)
        score += content_score * 20

        priority_score = self._get_priority_score(article)
        score += priority_score * 10

        return score

    def _get_recency_score(self, article: dict) -> float:
        """Score basado en tiempo desde publicación."""

        published_at = article.get("published_at")
        if not published_at:
            return 0.5

        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(
                    published_at.replace("Z", "+00:00")
                )
            except ValueError:
                return 0.5

        if not isinstance(published_at, datetime):
            return 0.5

        hours_ago = (datetime.now() - published_at).total_seconds() / 3600

        if hours_ago < 1:
            return 1.0
        elif hours_ago < 6:
            return 0.9
        elif hours_ago < 12:
            return 0.7
        elif hours_ago < 24:
            return 0.5
        else:
            return max(0, 0.5 - (hours_ago - 24) / 48)

    def _get_source_score(self, article: dict) -> float:
        """Score basado en fuente."""

        source = article.get("source", "").lower()

        for source_name, weight in self.SOURCE_WEIGHTS.items():
            if source_name in source:
                return weight

        return 0.5

    def _get_content_score(self, article: dict) -> float:
        """Score basado en calidad del contenido."""

        score = 0.5

        if article.get("image"):
            score += 0.2

        if article.get("description"):
            desc_len = len(article.get("description", ""))
            if 50 < desc_len < 300:
                score += 0.15
            elif desc_len >= 300:
                score += 0.1

        title = article.get("title", "")
        if title and 20 < len(title) < 120:
            score += 0.15

        return min(score, 1.0)

    def _get_priority_score(self, article: dict) -> float:
        """Score basado en palabras clave de urgencia."""

        title = article.get("title", "").lower()

        for keyword in self.URGENT_KEYWORDS:
            if keyword in title:
                return 1.0

        return 0.0
