from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_at: datetime
    category: str = "general"
    score: float = 0.0


class NewsRanker:
    def __init__(self, weights: dict = None):
        self.weights = weights or {
            "recency": 0.4,
            "source_trust": 0.3,
            "category": 0.2,
            "engagement": 0.1,
        }
        self.source_trust = {
            "unitel": 0.9,
            "red-uno": 0.85,
            "red-bolivision": 0.8,
            "radio-fides": 0.85,
            "opinion": 0.9,
            "el-deber": 0.9,
            "la-razon": 0.85,
        }

    def rank(self, news: list[NewsItem]) -> list[NewsItem]:
        for item in news:
            item.score = self._calculate_score(item)
        return sorted(news, key=lambda x: x.score, reverse=True)

    def _calculate_score(self, item: NewsItem) -> float:
        score = 0.0
        score += self._recency_score(item.published_at) * self.weights["recency"]
        score += self.source_trust.get(item.source, 0.5) * self.weights["source_trust"]
        score += self.weights.get(item.category, 0.2) * self.weights["category"]
        return score

    def _recency_score(self, published_at: datetime) -> float:
        hours_old = (datetime.now() - published_at).total_seconds() / 3600
        if hours_old < 1:
            return 1.0
        elif hours_old < 3:
            return 0.9
        elif hours_old < 6:
            return 0.7
        elif hours_old < 12:
            return 0.5
        elif hours_old < 24:
            return 0.3
        return 0.1
