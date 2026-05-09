import hashlib
from datetime import UTC, datetime, timedelta

import httpx
from loguru import logger


class NewsAPICollector:
    """Recolector de noticias usando NewsAPI.org."""

    BASE_URL = "https://newsapi.org/v2"

    CATEGORIES_MAP = {
        "economia": "business",
        "politica": "general",
        "deportes": "sports",
        "tecnologia": "technology",
        "entretenimiento": "entertainment",
        "general": "general",
    }

    CATEGORY_QUERIES = {
        "economia": "Bolivia AND (economia OR dolar OR banco OR finanzas)",
        "politica": "Bolivia AND (politica OR gobierno OR elecciones OR presidente)",
        "deportes": "Bolivia AND (deportes OR futbol OR liga OR seleccion)",
        "tecnologia": "Bolivia AND (tecnologia OR digital OR internet OR inteligencia artificial)",
        "entretenimiento": "Bolivia AND (entretenimiento OR cultura OR musica OR cine)",
        "general": "Bolivia",
    }

    TOP_HEADLINES_COUNTRIES = {
        "ae",
        "ar",
        "at",
        "au",
        "be",
        "bg",
        "br",
        "ca",
        "ch",
        "cn",
        "co",
        "cu",
        "cz",
        "de",
        "eg",
        "fr",
        "gb",
        "gr",
        "hk",
        "hu",
        "id",
        "ie",
        "il",
        "in",
        "it",
        "jp",
        "kr",
        "lt",
        "lv",
        "ma",
        "mx",
        "my",
        "ng",
        "nl",
        "no",
        "nz",
        "ph",
        "pl",
        "pt",
        "ro",
        "rs",
        "ru",
        "sa",
        "se",
        "sg",
        "si",
        "sk",
        "th",
        "tr",
        "tw",
        "ua",
        "us",
        "ve",
        "za",
    }

    def __init__(self, api_key: str, country: str = "bo", language: str = "es"):
        self.api_key = api_key
        self.country = country.lower()
        self.language = language

        if not api_key:
            logger.warning("NEWS_API_KEY no configurada. NewsAPI deshabilitado.")

        logger.info(
            f"NewsAPICollector inicializado para country={country}, language={language}"
        )

    async def fetch(self, categories: list[str] | None = None) -> list[dict]:
        """Obtiene noticias de NewsAPI."""

        if not self.api_key:
            logger.warning("NewsAPI deshabilitada - no hay API key")
            return []

        news = []
        categories = categories or ["general"]

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
        """Obtiene noticias de una categoria especifica."""

        if self.country not in self.TOP_HEADLINES_COUNTRIES:
            return await self._search_bolivia_category(client, category)

        api_category = self.CATEGORIES_MAP.get(category, "general")
        params = {
            "apiKey": self.api_key,
            "country": self.country,
            "category": api_category,
            "pageSize": 20,
        }

        try:
            response = await client.get(f"{self.BASE_URL}/top-headlines", params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                logger.warning(f"NewsAPI error: {data.get('message')}")
                return []

            articles = data.get("articles", [])
            logger.info(f"Obtenidas {len(articles)} noticias de {category}")
            for article in articles:
                article["_requested_category"] = category
            return articles

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error en NewsAPI: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error en NewsAPI: {e}")
            return []

    async def _search_bolivia_category(
        self, client: httpx.AsyncClient, category: str
    ) -> list[dict]:
        """Busca noticias de Bolivia con /everything cuando top-headlines no soporta el pais."""

        from_date = (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
        params = {
            "apiKey": self.api_key,
            "q": self.CATEGORY_QUERIES.get(category, self.CATEGORY_QUERIES["general"]),
            "language": self.language,
            "from": from_date,
            "sortBy": "publishedAt",
            "pageSize": 20,
        }

        try:
            response = await client.get(f"{self.BASE_URL}/everything", params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                logger.warning(f"NewsAPI search error: {data.get('message')}")
                return []

            articles = data.get("articles", [])
            logger.info(f"NewsAPI search obtuvo {len(articles)} noticias de {category}")
            for article in articles:
                article["_requested_category"] = category
            return articles

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error en NewsAPI search: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error en NewsAPI search: {e}")
            return []

    def _process_news(self, articles: list[dict]) -> list[dict]:
        """Procesa articulos de NewsAPI al formato interno."""

        processed = []

        for article in articles:
            if not article.get("title") or article.get("title") == "[Removed]":
                continue
            if self.country == "bo" and not self._mentions_bolivia(article):
                continue

            url = article.get("url", "")
            published_at = article.get("publishedAt")

            if published_at:
                try:
                    published_at = datetime.fromisoformat(
                        published_at.replace("Z", "+00:00")
                    )
                except ValueError:
                    published_at = datetime.now(UTC)
            else:
                published_at = datetime.now(UTC)

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
                    "category": article.get("_requested_category")
                    or self._infer_category(article),
                    "country": self.country,
                }
            )

        logger.info(f"Procesadas {len(processed)} noticias de NewsAPI")
        return processed

    def _infer_category(self, article: dict) -> str:
        """Infiere la categoria desde los metadatos."""

        title = article.get("title", "").lower()
        description = article.get("description", "").lower()

        keywords = {
            "economia": ["economia", "bolsa", "acciones", "dolar", "banco", "finanzas"],
            "politica": [
                "gobierno",
                "congreso",
                "presidente",
                "ministro",
                "ley",
                "politico",
                "elecciones",
            ],
            "deportes": [
                "futbol",
                "deporte",
                "liga",
                "copa",
                "gol",
                "equipo",
            ],
            "tecnologia": [
                "tecnologia",
                "tech",
                "app",
                "digital",
                "software",
                "ia",
                "inteligencia artificial",
            ],
            "entretenimiento": [
                "cine",
                "musica",
                "pelicula",
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

    def _mentions_bolivia(self, article: dict) -> bool:
        text = " ".join(
            str(article.get(field) or "")
            for field in ("title", "description", "content")
        ).lower()
        return "bolivia" in text or "bolivian" in text or "boliviana" in text
