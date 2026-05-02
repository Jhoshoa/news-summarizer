import httpx
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import hashlib
import re


from bs4 import BeautifulSoup
from loguru import logger
import yaml
from pathlib import Path


@dataclass
class NewsSource:
    name: str
    url: str
    category: str = "general"
    country: str = "bolivia"
    selector: str = "article"
    title_selector: str = "h2 a"
    url_selector: str = "a"
    date_selector: str = ".date"
    date_attr: str = None
    image_selector: str = "img"
    category_selector: str = None
    category_link_selector: str = None
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "NewsSource":
        return cls(
            name=data.get("name", "unknown"),
            url=data.get("url", ""),
            category=data.get("category", "general"),
            country=data.get("country", "bolivia"),
            selector=data.get("selector", "article"),
            title_selector=data.get("title_selector", "h2 a"),
            url_selector=data.get("url_selector", "a"),
            date_selector=data.get("date_selector", ".date"),
            date_attr=data.get("date_attr"),
            image_selector=data.get("image_selector", "img"),
            category_selector=data.get("category_selector"),
            category_link_selector=data.get("category_link_selector"),
            enabled=data.get("enabled", True),
        )


class NewsScraper:
    DEFAULT_SOURCES = [
        NewsSource(
            name="RadioFides",
            url="https://www.radiofides.com/",
            category="general",
            selector="article.post, article",
            title_selector="h2 a, h3 a",
            url_selector="a.post-link, a",
            date_selector=".post-date, .date, time",
        ),
        NewsSource(
            name="Unitel",
            url="https://unitel.bo/",
            category="general",
            selector="article, .noticia-item, .news-item",
            title_selector="h2 a, h3 a, .title a",
            url_selector="a",
            date_selector=".fecha, .date, time",
        ),
        NewsSource(
            name="RedUno",
            url="https://www.reduno.com.bo/",
            category="general",
            selector="article, .noticia, .news-item",
            title_selector="h2 a, h3 a",
            url_selector="a",
            date_selector=".fecha, .date-published, time",
        ),
        NewsSource(
            name="RedBolivision",
            url="https://www.redbolivision.tv.bo/",
            category="general",
            selector="article, .noticia-item, .news-item",
            title_selector="h2 a, h3 a",
            url_selector="a",
            date_selector=".fecha, time",
        ),
    ]

    def __init__(
        self,
        sources: list[dict] = None,
        user_agent: str = None,
        timeout: int = 30,
        config_path: str = None,
    ):
        self.user_agent = (
            user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.timeout = timeout
        self._config_path = config_path

        if sources:
            self.sources = [NewsSource.from_dict(s) if isinstance(s, dict) else s for s in sources]
        else:
            self.sources = self.DEFAULT_SOURCES

        if config_path:
            self._load_sources_from_config(config_path)

        logger.info(f"NewsScraper inicializado con {len(self.sources)} fuentes")

    def reload_config(self):
        if self._config_path:
            self._load_sources_from_config(self._config_path)

    def _load_sources_from_config(self, config_path: str):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if config and "sources" in config:
                self.sources = [
                    NewsSource.from_dict(s) for s in config["sources"] if s.get("enabled", True)
                ]
                logger.info(f"Cargadas {len(self.sources)} fuentes desde {config_path}")
        except Exception as e:
            logger.warning(f"Error cargando config: {e}. Usando fuentes por defecto.")

    async def fetch_all(self, categories: list[str] = None) -> list[dict]:
        results = []

        timeout = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            for source in self.sources:
                if categories and source.category not in categories:
                    continue
                try:
                    news = await self._scrape_source(client, source)
                    results.extend(news)
                    logger.info(f"Scraped {len(news)} noticias de {source.name}")
                except Exception as e:
                    logger.error(f"Error scraping {source.name}: {e}")

        return self._deduplicate(results)

    async def _scrape_source(self, client, source: NewsSource) -> list[dict]:
        try:
            response = await client.get(source.url)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, "lxml")
            articles = []
            for article in soup.select(source.selector):
                try:
                    news = self._extract_article(article, source)
                    if news:
                        articles.append(news)
                except Exception as e:
                    logger.warning(f"Error extracting article: {e}")

            if not articles:
                logger.warning(
                    f"No articles found for {source.name}. HTML length: {len(html)}. Checking selectors: {source.selector}"
                )
            return articles
        except Exception as e:
            logger.error(f"Error fetching {source.name}: {e}")
            return []

    def _extract_article(self, article_soup, source: NewsSource) -> Optional[dict]:
        try:
            title_elem = article_soup.select_one(source.title_selector)
            print("------------------------->>>>>>>>>>>>>>>>---------------")
            print(source.title_selector)
            print(title_elem)
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 10:
                return None

            url = self._extract_url(article_soup, source)
            if not url:
                return None

            published_at = self._extract_date(article_soup, source)
            image = self._extract_image(article_soup, source)
            category = self._extract_category(article_soup, source)

            return {
                "title": title,
                "url": url,
                "source": source.name,
                "category": category,
                "country": source.country,
                "published_at": published_at,
                "image": image,
                "hash": hashlib.md5(url.encode()).hexdigest() if url else None,
            }
        except Exception as e:
            logger.warning(f"Error extracting article: {e}")
            return None

    def _extract_url(self, article_soup, source: NewsSource) -> str:
        url = ""
        if source.url_selector:
            url_elem = article_soup.select_one(source.url_selector)
            if url_elem:
                url = url_elem.get("href", "")
        if not url and article_soup.name == "a":
            url = article_soup.get("href", "")
        if not url:
            title_elem = article_soup.select_one(source.title_selector)
            if title_elem:
                url = title_elem.get("href", "")
        if url and not url.startswith("http"):
            url = source.url.rstrip("/") + url
        return url

    def _extract_date(self, article_soup, source: NewsSource) -> datetime:
        if not source.date_selector:
            return datetime.now()
        date_elem = article_soup.select_one(source.date_selector)
        if not date_elem:
            return datetime.now()
        if source.date_attr:
            date_text = date_elem.get(source.date_attr, "")
        elif date_elem.name in ("input", "textarea", "select"):
            date_text = date_elem.get("value", "")
        else:
            date_text = date_elem.get_text(strip=True)
        return self._parse_date(date_text)

    def _extract_image(self, article_soup, source: NewsSource) -> Optional[str]:
        if not source.image_selector:
            return None
        image_elem = article_soup.select_one(source.image_selector)
        if not image_elem:
            return None
        return (
            image_elem.get("src")
            or image_elem.get("data-src")
            or image_elem.get("data-lazy-src")
            or (image_elem.get("srcset", "").split()[0] if image_elem.get("srcset") else None)
        )

    def _extract_category(self, article_soup, source: NewsSource) -> str:
        if source.category_selector:
            cat_elem = article_soup.select_one(source.category_selector)
            if cat_elem:
                return cat_elem.get_text(strip=True)
        return source.category

    def _parse_date(self, date_text: str) -> datetime:
        if not date_text:
            return datetime.now()

        from dateutil import parser

        date_text = date_text.lower()
        date_text = re.sub(r"hace \d+ horas?", "", date_text)
        date_text = re.sub(r"ayer", "1 day ago", date_text)
        date_text = re.sub(r"hoy", "", date_text)

        try:
            return parser.parse(date_text, fuzzy=True)
        except:
            return datetime.now()

    def _deduplicate(self, news: list[dict]) -> list[dict]:
        seen = set()
        unique = []

        for article in news:
            if article.get("hash") and article["hash"] not in seen:
                seen.add(article["hash"])
                unique.append(article)
            elif not article.get("hash"):
                unique.append(article)

        logger.info(f"Deduplicado: {len(news)} -> {len(unique)} noticias")
        return unique
