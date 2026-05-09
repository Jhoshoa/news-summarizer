from datetime import UTC, datetime


class NewsRanker:
    def __init__(self, weights: dict | None = None):
        self.weights = weights or {
            "recency": 0.45,
            "source_trust": 0.35,
            "category_match": 0.20,
        }
        self.source_trust = {
            "unitel": 0.9,
            "reduno": 0.85,
            "red uno": 0.85,
            "redbolivision": 0.8,
            "red bolivision": 0.8,
            "radiofides": 0.85,
            "radio fides": 0.85,
            "opinion": 0.9,
            "el deber": 0.9,
            "la razon": 0.85,
        }

    def rank(self, news: list[dict], limit: int | None = None) -> list[dict]:
        for item in news:
            item["score"] = self._calculate_score(item)

        ranked = sorted(news, key=lambda item: item.get("score", 0), reverse=True)
        return ranked[:limit] if limit else ranked

    def _calculate_score(self, item: dict) -> float:
        source = str(item.get("source", "")).lower()
        category = item.get("category", "general")

        score = 0.0
        score += self._recency_score(item.get("published_at")) * self.weights["recency"]
        score += self.source_trust.get(source, 0.5) * self.weights["source_trust"]
        score += (0.6 if category != "general" else 0.2) * self.weights["category_match"]
        return score

    def _recency_score(self, published_at: datetime | None) -> float:
        if not isinstance(published_at, datetime):
            return 0.2

        now = datetime.now(UTC) if published_at.tzinfo else datetime.now()
        hours_old = max((now - published_at).total_seconds() / 3600, 0)

        if hours_old < 1:
            return 1.0
        if hours_old < 3:
            return 0.9
        if hours_old < 6:
            return 0.7
        if hours_old < 12:
            return 0.5
        if hours_old < 24:
            return 0.3
        return 0.1
