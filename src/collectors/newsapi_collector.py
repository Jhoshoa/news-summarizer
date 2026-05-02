from datetime import datetime
from typing import Optional
import hashlib

import httpx
from loguru import logger


class NewsAPICollector:
    """Recolector de noticias usando NewsAPI.org."""

    BASE_URL = "https://newsapi.org/v2"

    CATEGORIES_MAP = {
        "economia": "business",
        "politica": "politics",
        "deportes": "sports",
        "tecnologia": "technology",
        "entretenimiento": "entertainment",
        "general": "general",
    }

    def __init__(self, api_key: str, country: str = "bo", language: str = "es"):
        self.api_key = api_key
        self.country = country
        self.language = language

        if not api_key:
            logger.warning("NEWS_API_KEY no configurada. NewsAPI deshabilitado.")

        logger.info(
            f"NewsAPICollector inicializado para country={country}, language={language}"
        )

    async def fetch(self, categories: list[str] = None) -> list[dict]:
        """Obtiene noticias de NewsAPI."""

        if not self.api_key:
            logger.warning("NewsAPI deshabilitada - no hay API key")
            return []

        news = []

        if not categories:
            categories = ["general"]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for category in categories:
                try:
                    cat_news = await self._fetch_category(client, category)
                    news.extend(cat_news)
                except Exception as e:
                    logger.error(f"Error fetching category {category}: {e}")

        return self._process_news(news)

    async def _fetch_category(
        self, client: httpx.AsyncClient, category: str
    ) -> list[dict]:
        """Obtiene noticias de una categoría específica."""

        api_category = self.CATEGORIES_MAP.get(category, "general")

        params = {
            "apiKey": self.api_key,
            "country": self.country,
            "language": self.language,
            "category": api_category,
            "pageSize": 20,
        }

        try:
            response = await client.get(f"{self.BASE_URL}/top-headlines", params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("status") == "ok":
                articles = data.get("articles", [])
                logger.info(f"Obtenidas {len(articles)} noticias de {category}")
                return articles
            else:
                logger.warning(f"NewsAPI error: {data.get('message')}")
                return []

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error en NewsAPI: {e}")
            return []
        except Exception as e:
            logger.error(f"Error en NewsAPI: {e}")
            return []

    def _process_news(self, articles: list[dict]) -> list[dict]:
        """Procesa artículos de NewsAPI al formato interno."""

        processed = []

        for article in articles:
            if not article.get("title") or article.get("title") == "[Removed]":
                continue

            url = article.get("url", "")
            published_at = article.get("publishedAt")

            if published_at:
                try:
                    published_at = datetime.fromisoformat(
                        published_at.replace("Z", "+00:00")
                    )
                except:
                    published_at = datetime.now()
            else:
                published_at = datetime.now()

            processed.append(
                {
                    "title": article.get("title", ""),
                    "url": url,
                    "description": article.get("description", ""),
                    "source": article.get("source", {}).get("name", "NewsAPI"),
                    "author": article.get("author"),
                    "published_at": published_at,
                    "image": article.get("urlToImage"),
                    "hash": hashlib.md5(url.encode()).hexdigest() if url else None,
                    "category": self._infer_category(article),
                    "country": self.country,
                }
            )

        logger.info(f"Procesadas {len(processed)} noticias de NewsAPI")
        return processed

    def _infer_category(self, article: dict) -> str:
        """Infiere la categoría desde los metadatos."""

        title = article.get("title", "").lower()
        description = article.get("description", "").lower()
        source = article.get("source", {}).get("name", "").lower()

        keywords = {
            "economia": ["economía", "bolsa", "acciones", "dólar", "banco", "finanzas"],
            "politica": [
                "gobierno",
                "congreso",
                "presidente",
                "ministro",
                "ley",
                "político",
            ],
            "deportes": [
                "fútbol",
                "futbol",
                "deporte",
                "liga",
                "copa",
                "gol",
                "equipo",
            ],
            "tecnologia": [
                "tecnología",
                "tech",
                "app",
                "digital",
                "software",
                "ia",
                "inteligencia artificial",
            ],
            "entretenimiento": [
                "cine",
                "música",
                "película",
                "serie",
                "actor",
                "celebridad",
            ],
        }

        text = f"{title} {description}"

        for category, words in keywords.items():
            if any(word in text for word in words):
                return category

        return "general"
