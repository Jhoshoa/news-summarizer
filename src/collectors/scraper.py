import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import httpx
import yaml
from bs4 import BeautifulSoup
from loguru import logger


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
    body_selector: str = None
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
            body_selector=data.get("body_selector"),
            category_selector=data.get("category_selector"),
            category_link_selector=data.get("category_link_selector"),
            enabled=data.get("enabled", True),
        )


class NewsScraper:
    DEFAULT_BODY_SELECTOR = (
        "article [itemprop='articleBody'], "
        "article .entry-content, "
        "article .post-content, "
        "article .article-content, "
        "article .nota-contenido, "
        "article .news-detail, "
        "article .single-content, "
        "article .content, "
        "main [itemprop='articleBody'], "
        "main .entry-content, "
        "main .post-content, "
        "main .article-content, "
        "main .nota-contenido, "
        "main .news-detail, "
        "main .single-content, "
        "main .content, "
        "article p, "
        "main p"
    )
    BODY_EXCLUDE_SELECTOR = (
        "script, style, noscript, iframe, form, nav, header, footer, aside, "
        ".ad, .ads, .advertisement, .publicidad, .banner, .share, .social, "
        ".related, .relacionadas, .tags, .tag, .newsletter, .comments"
    )
    MIN_CONTENT_WORDS = 25

    DEFAULT_SOURCES = [
        NewsSource(
            name="RadioFides",
            url="https://www.radiofides.com/",
            category="general",
            selector="article.post, article",
            title_selector="h2 a, h3 a",
            url_selector="a.post-link, a",
            date_selector=".post-date, .date, time",
            body_selector=".entry-content, .post-content, article .content, article p",
        ),
        NewsSource(
            name="Unitel",
            url="https://unitel.bo/",
            category="general",
            selector="article, .noticia-item, .news-item",
            title_selector="h2 a, h3 a, .title a",
            url_selector="a",
            date_selector=".fecha, .date, time",
            body_selector=(
                "main article p, main section p, "
                ".article-body p, .nota-contenido p, .news-detail p"
            ),
        ),
        NewsSource(
            name="RedUno",
            url="https://www.reduno.com.bo/",
            category="general",
            selector="article, .noticia, .news-item",
            title_selector="h2 a, h3 a",
            url_selector="a",
            date_selector=".fecha, .date-published, time",
            body_selector="article p, main p, .nota__body p, .nota-contenido p",
        ),
        NewsSource(
            name="RedBolivision",
            url="https://www.redbolivision.tv.bo/",
            category="general",
            selector="article, .noticia-item, .news-item",
            title_selector="h2 a, h3 a",
            url_selector="a",
            date_selector=".fecha, time",
            body_selector="article p, main p, .entry-content p, .post-content p",
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
            with open(config_path, encoding="utf-8") as f:
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

        timeout = httpx.Timeout(float(self.timeout), connect=min(10.0, float(self.timeout)))
        async with httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            for source in self.sources:
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
                articles = self._extract_links_fallback(soup, source)

            articles = self._deduplicate(articles)
            return await self._enrich_articles(client, articles, source)
        except Exception as e:
            logger.error(f"Error fetching {source.name}: {e}")
            return []

    def _extract_article(self, article_soup, source: NewsSource) -> dict | None:
        try:
            title_elem = article_soup.select_one(source.title_selector)
            if not title_elem and article_soup.name == "a":
                title_elem = article_soup
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
                "source_type": "scraper",
                "source_url": source.url,
                "category": category,
                "country": source.country,
                "published_at": published_at,
                "image": image,
                "hash": hashlib.md5(url.encode()).hexdigest() if url else None,
            }
        except Exception as e:
            logger.warning(f"Error extracting article: {e}")
            return None

    def _extract_links_fallback(self, soup: BeautifulSoup, source: NewsSource) -> list[dict]:
        articles = []
        seen_urls = set()

        for link in soup.select("a[href]"):
            title = link.get_text(" ", strip=True)
            if not title or len(title) < 20:
                continue

            url = urljoin(source.url, link.get("href", ""))
            if not self._looks_like_article_url(url, source) or url in seen_urls:
                continue

            seen_urls.add(url)
            articles.append(
                {
                    "title": title,
                    "url": url,
                    "source": source.name,
                    "source_type": "scraper",
                    "source_url": source.url,
                    "category": source.category,
                    "country": source.country,
                    "published_at": datetime.now(),
                    "image": None,
                    "hash": hashlib.md5(url.encode()).hexdigest(),
                }
            )

        logger.info(f"Fallback extracted {len(articles)} noticias de {source.name}")
        return articles

    async def _enrich_articles(
        self,
        client: httpx.AsyncClient,
        articles: list[dict],
        source: NewsSource,
    ) -> list[dict]:
        enriched = []

        for article in articles:
            try:
                enriched.append(await self._enrich_article(client, article, source))
            except Exception as e:
                logger.warning(f"Error enriching article {article.get('url')}: {e}")
                enriched.append(article)

        return enriched

    async def _enrich_article(
        self,
        client: httpx.AsyncClient,
        article: dict,
        source: NewsSource,
    ) -> dict:
        url = article.get("url")
        if not url:
            return article

        try:
            response = await client.get(url)
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"Error fetching article detail for {url}: {e}")
            return article

        soup = BeautifulSoup(response.text, "lxml")
        content = self._extract_body_content(soup, source)
        word_count = self._count_words(content)

        if not content:
            logger.warning(
                f"No body content extracted for {source.name}: {url}. "
                f"Selector: {source.body_selector or self.DEFAULT_BODY_SELECTOR}"
            )

        article["content"] = content or None
        article["excerpt"] = self._build_excerpt(content) if content else None
        article["content_word_count"] = word_count
        article["content_collected_at"] = datetime.now()

        if content and not article.get("description"):
            article["description"] = article["excerpt"]

        detail_image = self._extract_image(soup, source)
        if detail_image and not article.get("image"):
            article["image"] = detail_image

        return article

    def _extract_body_content(self, soup: BeautifulSoup, source: NewsSource) -> str:
        json_ld_content = self._extract_json_ld_article_body(soup)
        if json_ld_content:
            return json_ld_content

        if source.body_selector:
            content = self._extract_content_with_selector(
                soup,
                source,
                source.body_selector,
            )
            if content:
                return content

        selectors = [self.DEFAULT_BODY_SELECTOR]
        best_content = ""

        for selector in selectors:
            content = self._extract_content_with_selector(soup, source, selector)
            if self._count_words(content) >= self.MIN_CONTENT_WORDS:
                return content

            if len(content) > len(best_content):
                best_content = content

        fallback_content = self._extract_readable_text_fallback(soup)
        if self._count_words(fallback_content) > self._count_words(best_content):
            return fallback_content

        return best_content

    def _extract_json_ld_article_body(self, soup: BeautifulSoup) -> str:
        candidates = []

        for script in soup.select("script[type='application/ld+json']"):
            raw_json = script.string or script.get_text(strip=True)
            if not raw_json:
                continue

            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                continue

            candidates.extend(self._iter_json_ld_nodes(data))

        text_parts = []
        for node in candidates:
            node_type = node.get("@type")
            node_types = node_type if isinstance(node_type, list) else [node_type]
            if not any(item in ("NewsArticle", "Article", "ReportageNewsArticle") for item in node_types):
                continue

            article_body = node.get("articleBody")
            if article_body:
                text_parts.append(str(article_body))
            elif node.get("description"):
                text_parts.append(str(node["description"]))

        return self._clean_text("\n\n".join(text_parts))

    def _iter_json_ld_nodes(self, data):
        if isinstance(data, dict):
            yield data
            graph = data.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    yield from self._iter_json_ld_nodes(item)
        elif isinstance(data, list):
            for item in data:
                yield from self._iter_json_ld_nodes(item)

    def _extract_readable_text_fallback(self, soup: BeautifulSoup) -> str:
        for excluded in soup.select(self.BODY_EXCLUDE_SELECTOR):
            excluded.decompose()

        for excluded in soup.select("nav, header, footer, aside"):
            excluded.decompose()

        lines = [
            self._clean_text(line)
            for line in soup.get_text("\n", strip=True).splitlines()
        ]
        lines = [line for line in lines if line]

        title_index = self._find_article_title_line(lines)
        if title_index is None:
            return ""

        body_lines = []
        for line in lines[title_index + 1 :]:
            normalized = self._normalize_text_for_filtering(line)

            if self._is_article_stop_line(normalized):
                break
            if self._is_noise_line(normalized):
                continue
            if len(line) < 35:
                continue

            body_lines.append(line)

        return "\n\n".join(dict.fromkeys(body_lines))

    def _find_article_title_line(self, lines: list[str]) -> int | None:
        for index, line in enumerate(lines):
            if len(line) >= 45 and not self._is_noise_line(
                self._normalize_text_for_filtering(line)
            ):
                return index
        return None

    def _is_article_stop_line(self, normalized: str) -> bool:
        stop_markers = (
            "recibe las noticias",
            "ultimas noticias",
            "últimas noticias",
            "tambien te puede interesar",
            "también te puede interesar",
            "siga unitel",
            "sobre unitel",
            "noticias relacionadas",
            "te puede interesar",
        )
        return any(marker in normalized for marker in stop_markers)

    def _is_noise_line(self, normalized: str) -> bool:
        noise_markers = (
            "facebook",
            "twitter",
            "whatsapp",
            "instagram",
            "tiktok",
            "publicacion:",
            "publicación:",
            "unitel digital",
            "mira aqui",
            "mira aquí",
            "direccion de correo",
            "dirección de correo",
            "indica que es obligatorio",
            "real people should not fill",
        )
        return any(marker in normalized for marker in noise_markers)

    def _normalize_text_for_filtering(self, text: str) -> str:
        return text.lower().strip()

    def _extract_content_with_selector(
        self,
        soup: BeautifulSoup,
        source: NewsSource,
        selector: str,
    ) -> str:
        try:
            elements = soup.select(selector)
        except Exception as e:
            logger.warning(f"Invalid body selector for {source.name}: {selector}. {e}")
            return ""

        return self._text_from_elements(elements)

    def _text_from_elements(self, elements) -> str:
        seen = set()
        paragraphs = []

        for element in elements:
            for excluded in element.select(self.BODY_EXCLUDE_SELECTOR):
                excluded.decompose()

            text_nodes = element.select("p, li, blockquote")
            if not text_nodes:
                text_nodes = [element]

            for node in text_nodes:
                text = self._clean_text(node.get_text(" ", strip=True))
                key = text.lower()
                if len(text) < 30 or key in seen:
                    continue
                seen.add(key)
                paragraphs.append(text)

        return "\n\n".join(paragraphs)

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        return text

    def _count_words(self, text: str | None) -> int:
        if not text:
            return 0
        return len(re.findall(r"\b\w+\b", text))

    def _build_excerpt(self, content: str, max_length: int = 280) -> str:
        excerpt = self._clean_text(content)
        if len(excerpt) <= max_length:
            return excerpt

        truncated = excerpt[:max_length].rsplit(" ", 1)[0].strip()
        return f"{truncated}..."

    def _looks_like_article_url(self, url: str, source: NewsSource) -> bool:
        if not url.startswith(source.url.rstrip("/")):
            return False

        blocked_fragments = (
            "/tag/",
            "/category/",
            "/categoria/",
            "/author/",
            "/page/",
            "facebook.com",
            "instagram.com",
            "twitter.com",
            "youtube.com",
            "tiktok.com",
        )
        if any(fragment in url for fragment in blocked_fragments):
            return False

        path = url.removeprefix(source.url.rstrip("/")).strip("/")
        return bool(path and len(path) > 8)

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
        if url:
            url = urljoin(source.url, url)
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

    def _extract_image(self, article_soup, source: NewsSource) -> str | None:
        if not source.image_selector:
            return None
        image_elem = article_soup.select_one(source.image_selector)
        if not image_elem:
            return None
        image_url = (
            image_elem.get("src")
            or image_elem.get("data-src")
            or image_elem.get("data-lazy-src")
            or (image_elem.get("srcset", "").split()[0] if image_elem.get("srcset") else None)
        )
        if not image_url:
            return None

        image_url = urljoin(source.url, image_url)
        return None if self._is_non_article_image(image_url) else image_url

    def _is_non_article_image(self, image_url: str) -> bool:
        normalized = image_url.lower()
        blocked_fragments = (
            "logo",
            "favicon",
            "icon",
            "placeholder",
            "avatar",
        )
        return any(fragment in normalized for fragment in blocked_fragments)

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
        except Exception:
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
