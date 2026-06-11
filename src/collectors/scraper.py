import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from html import unescape
from urllib.parse import urljoin, urlparse

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
            date_selector=".UNITEL_DETALLE_FECHA_PUBLICACION, .fecha, .date, time",
            image_selector="div[frame='imagenPrincipalNota_B'] img, meta[property='og:image'], img",
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
            body_selector=(
                ".body__cuerpo p, .contenedor.body p, .item.is-body .body__cuerpo p, "
                "article p, main p, .nota__body p, .nota-contenido p"
            ),
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
            articles = self._filter_articles_for_detail_fetch(articles, source)
            enriched = await self._enrich_articles(client, articles, source)
            return self._filter_usable_articles(enriched, source)
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
            title = self._clean_text(title_elem.get_text(" ", strip=True))
            if not title or len(title) < 10:
                return None

            url = self._extract_url(article_soup, source)
            if not url:
                return None

            listing_date = self._extract_optional_date(article_soup, source)
            if listing_date is None:
                listing_date = self._extract_date_from_url(url)
            published_at = listing_date or datetime.now()
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
                "published_at_from_listing": listing_date is not None,
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
            title = self._clean_text(link.get_text(" ", strip=True))
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
                    "published_at_from_listing": False,
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

    def _filter_usable_articles(self, articles: list[dict], source: NewsSource) -> list[dict]:
        usable = [
            article
            for article in articles
            if self._has_usable_text(article)
            and not self._has_future_publish_date(article)
            and not self._has_non_today_detail_skip(article)
        ]
        dropped = len(articles) - len(usable)
        if dropped:
            logger.info(f"Dropped {dropped} unusable articles from {source.name}")
        return usable

    def _has_usable_text(self, article: dict) -> bool:
        title = self._normalize_for_match(article.get("title", ""))
        text = " ".join(
            str(article.get(field) or "")
            for field in ("description", "content", "excerpt")
        ).strip()
        normalized_text = self._normalize_for_match(text)

        if not normalized_text or normalized_text == title:
            return False

        return self._count_words(text) >= 8 or len(text) >= 50

    def _has_future_publish_date(self, article: dict) -> bool:
        published_at = article.get("published_at")
        if not isinstance(published_at, datetime):
            return False

        return published_at > datetime.now() + timedelta(days=1)

    def _has_non_today_detail_skip(self, article: dict) -> bool:
        return article.get("skipped_detail_reason") == "non_today_detail_date"

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
        detail_date = self._extract_detail_date(soup, source)
        if detail_date:
            article["published_at"] = detail_date
            article["published_at_from_detail"] = True
            if self._has_non_today_publish_date(detail_date):
                article["skipped_detail_reason"] = "non_today_detail_date"
                return article

        content = self._extract_body_content(soup, source, article.get("title"))
        word_count = self._count_words(content)
        meta_description = self._extract_meta_description(soup)

        if not content:
            logger.warning(
                f"No body content extracted for {source.name}: {url}. "
                f"Selector: {source.body_selector or self.DEFAULT_BODY_SELECTOR}"
            )

        article["content"] = content or None
        article["excerpt"] = self._build_excerpt(content) if content else None
        article["content_word_count"] = word_count
        article["content_collected_at"] = datetime.now()
        if meta_description and not article.get("description"):
            article["description"] = meta_description
        elif content and not article.get("description"):
            article["description"] = article["excerpt"]

        detail_image = self._extract_image(soup, source)
        if detail_image and not article.get("image"):
            article["image"] = detail_image

        return article

    def _filter_articles_for_detail_fetch(
        self,
        articles: list[dict],
        source: NewsSource,
    ) -> list[dict]:
        filtered = [
            article
            for article in articles
            if not self._has_non_today_listing_publish_date(article)
        ]
        dropped = len(articles) - len(filtered)
        if dropped:
            logger.info(
                f"Skipped {dropped} non-today listing articles before detail fetch "
                f"from {source.name}"
            )
        return filtered

    def _has_non_today_listing_publish_date(self, article: dict) -> bool:
        if not article.get("published_at_from_listing"):
            return False

        published_at = article.get("published_at")
        if not isinstance(published_at, datetime):
            return False

        return self._has_non_today_publish_date(published_at)

    def _has_non_today_publish_date(self, published_at: datetime) -> bool:
        return published_at.date() != datetime.now().date()

    def _extract_detail_date(self, soup: BeautifulSoup, source: NewsSource) -> datetime | None:
        date_candidates = []

        if source.date_selector:
            for element in soup.select(source.date_selector):
                date_candidates.append(self._extract_date_text(element, source))

        for selector, attr in (
            ("meta[property='article:published_time']", "content"),
            ("meta[name='article:published_time']", "content"),
            ("meta[property='og:published_time']", "content"),
            ("time[datetime]", "datetime"),
        ):
            element = soup.select_one(selector)
            if element:
                date_candidates.append(element.get(attr, ""))

        date_candidates.extend(self._extract_json_ld_dates(soup))

        for candidate in date_candidates:
            parsed = self._parse_date(candidate, fallback_to_now=False)
            if parsed:
                return parsed
        return None

    def _extract_body_content(
        self,
        soup: BeautifulSoup,
        source: NewsSource,
        article_title: str | None = None,
    ) -> str:
        json_ld_content = self._extract_json_ld_article_body(soup)
        if json_ld_content:
            return json_ld_content

        if self._should_prefer_source_body_selector(source):
            content = self._extract_content_with_selector(
                soup,
                source,
                source.body_selector,
            )
            if self._count_words(content) >= self.MIN_CONTENT_WORDS:
                return content

        title_anchored_content = self._extract_readable_text_fallback(
            soup,
            source,
            article_title=article_title,
        )
        if self._count_words(title_anchored_content) >= self.MIN_CONTENT_WORDS:
            return title_anchored_content

        if source.body_selector:
            content = self._extract_content_with_selector(
                soup,
                source,
                source.body_selector,
            )
            if self._count_words(content) >= self.MIN_CONTENT_WORDS:
                return content

        selectors = [self.DEFAULT_BODY_SELECTOR]
        best_content = ""

        for selector in selectors:
            content = self._extract_content_with_selector(soup, source, selector)
            if self._count_words(content) >= self.MIN_CONTENT_WORDS:
                return content

            if len(content) > len(best_content):
                best_content = content

        fallback_content = self._extract_readable_text_fallback(soup, source)
        if self._count_words(fallback_content) > self._count_words(best_content):
            return fallback_content

        return best_content

    def _should_prefer_source_body_selector(self, source: NewsSource) -> bool:
        source_name = source.name.lower()
        selector = source.body_selector or ""
        return source_name in {"reduno", "red uno"} and ".body__cuerpo" in selector

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

        return self._clean_text("\n\n".join(text_parts))

    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        for selector in (
            "meta[property='og:description']",
            "meta[name='description']",
            "meta[name='twitter:description']",
        ):
            element = soup.select_one(selector)
            if not element:
                continue
            content = self._clean_text(element.get("content", ""))
            if content:
                return content
        return ""

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

    def _extract_readable_text_fallback(
        self,
        soup: BeautifulSoup,
        source: NewsSource,
        article_title: str | None = None,
    ) -> str:
        for excluded in soup.select(self.BODY_EXCLUDE_SELECTOR):
            excluded.decompose()

        for excluded in soup.select("nav, header, footer, aside"):
            excluded.decompose()

        lines = [
            self._clean_text(line)
            for line in soup.get_text("\n", strip=True).splitlines()
        ]
        lines = [line for line in lines if line]

        title_index = self._find_article_title_line(lines, article_title)
        if title_index is None:
            return ""

        body_lines = []
        skip_next_line = False
        for line in lines[title_index + 1 :]:
            normalized = self._normalize_text_for_filtering(line)

            if skip_next_line:
                skip_next_line = False
                continue
            if "te puede interesar" in normalized:
                skip_next_line = True
                continue
            if self._is_article_stop_line(normalized, source):
                break
            if self._is_noise_line(normalized):
                continue
            if len(line) < 35:
                continue
            if body_lines and self._looks_like_new_article_title(line, source):
                break

            body_lines.append(line)

        return "\n\n".join(dict.fromkeys(body_lines))

    def _find_article_title_line(
        self,
        lines: list[str],
        article_title: str | None = None,
    ) -> int | None:
        if article_title:
            expected_title = self._normalize_for_match(article_title)
            for index, line in enumerate(lines):
                candidate = self._normalize_for_match(line)
                if not candidate:
                    continue

                similarity = SequenceMatcher(None, expected_title, candidate).ratio()
                if similarity >= 0.72 or expected_title in candidate or candidate in expected_title:
                    return index

        for index, line in enumerate(lines):
            if len(line) >= 45 and not self._is_noise_line(
                self._normalize_text_for_filtering(line)
            ):
                return index
        return None

    def _is_article_stop_line(self, normalized: str, source: NewsSource) -> bool:
        stop_markers = (
            "recibe las noticias",
            "ultimas noticias",
            "últimas noticias",
            "siga unitel",
            "sobre unitel",
            "noticias relacionadas",
            "comentarios",
            "mas leidas",
            "más leídas",
            "mas noticias",
            "más noticias",
            "programacion",
            "programación",
            "temas relacionados",
            "seguinos en",
            "terminos y condiciones",
            "términos y condiciones",
            "politica de privacidad",
            "política de privacidad",
        )
        if source.name.lower() not in {"reduno", "red uno"}:
            stop_markers += (
                "tambien te puede interesar",
                "también te puede interesar",
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
            "te puede interesar",
            "direccion de correo",
            "dirección de correo",
            "indica que es obligatorio",
            "real people should not fill",
            "publicidad",
            "escuchar esta nota",
            "mira la programacion",
            "mira la programación",
        )
        return any(marker in normalized for marker in noise_markers)

    def _looks_like_new_article_title(self, line: str, source: NewsSource) -> bool:
        if source.name.lower() not in {"redbolivision", "red bolivision"}:
            return False

        if len(line) > 160:
            return False

        return not line.endswith((".", ",", ";", ":"))

    def _normalize_text_for_filtering(self, text: str) -> str:
        return text.lower().strip()

    def _normalize_for_match(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", str(text).lower())
        normalized = "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

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
        text = str(text or "")
        for _ in range(3):
            unescaped = unescape(text)
            if unescaped == text:
                break
            text = unescaped

        text = self._fix_mojibake(text)
        if re.search(r"</?[a-zA-Z][^>]*>", text):
            text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)

        text = text.replace("\xa0", " ")
        text = text.replace("\u00ad", "")
        text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _fix_mojibake(self, text: str) -> str:
        if not any(marker in text for marker in ("Ã", "Â", "â")):
            return text

        replacements = {
            "â€œ": '"',
            "â€\x9d": '"',
            "â€˜": "'",
            "â€™": "'",
            "â€“": "-",
            "â€”": "-",
            "â€¦": "...",
            "Â": "",
        }
        candidate = text
        for broken, fixed_value in replacements.items():
            candidate = candidate.replace(broken, fixed_value)
        candidate = re.sub(
            r"Ã([\x80-\xbf])",
            lambda match: bytes((0xC3, ord(match.group(1)))).decode("utf-8"),
            candidate,
        )

        fixed = None
        for encoding in ("latin1", "cp1252"):
            try:
                fixed = candidate.encode(encoding).decode("utf-8")
                break
            except UnicodeError:
                continue

        if fixed is None:
            fixed = candidate

        original_markers = sum(text.count(marker) for marker in ("Ã", "Â", "â"))
        fixed_markers = sum(fixed.count(marker) for marker in ("Ã", "Â", "â"))
        return fixed if fixed_markers < original_markers else text

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
        parsed_url = urlparse(url)
        parsed_source = urlparse(source.url)

        if parsed_url.netloc != parsed_source.netloc:
            return False

        blocked_fragments = (
            "/tag/",
            "/category/",
            "/categoria/",
            "/author/",
            "/page/",
            "/programa/",
            "facebook.com",
            "instagram.com",
            "twitter.com",
            "youtube.com",
            "tiktok.com",
        )
        if any(fragment in url for fragment in blocked_fragments):
            return False

        path = parsed_url.path.strip("/")
        source_path = parsed_source.path.strip("/")
        if source_path and path == source_path:
            return False

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
        return self._extract_optional_date(article_soup, source) or datetime.now()

    def _extract_optional_date(self, article_soup, source: NewsSource) -> datetime | None:
        if not source.date_selector:
            return None
        date_elem = article_soup.select_one(source.date_selector)
        if not date_elem:
            return None
        date_text = self._extract_date_text(date_elem, source)
        return self._parse_date(date_text, fallback_to_now=False)

    def _extract_date_text(self, date_elem, source: NewsSource) -> str:
        if source.date_attr and date_elem.has_attr(source.date_attr):
            return date_elem.get(source.date_attr, "")
        elif date_elem.name in ("input", "textarea", "select"):
            return date_elem.get("value", "")
        return date_elem.get_text(strip=True)

    def _extract_date_from_url(self, url: str) -> datetime | None:
        match = re.search(r"/(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?:/|$)", url)
        if match:
            try:
                return datetime(
                    int(match.group("year")),
                    int(match.group("month")),
                    int(match.group("day")),
                )
            except ValueError:
                return None

        stamp_match = re.search(r"(?P<stamp>20\d{10,11})(?:\D|$)", url)
        if not stamp_match:
            return None

        stamp = stamp_match.group("stamp")
        for month_digits in (2, 1):
            try:
                year = int(stamp[:4])
                month_start = 4
                day_start = month_start + month_digits
                hour_start = day_start + 2
                minute_start = hour_start + 2
                second_start = minute_start + 2
                return datetime(
                    year,
                    int(stamp[month_start:day_start]),
                    int(stamp[day_start:hour_start]),
                    int(stamp[hour_start:minute_start]),
                    int(stamp[minute_start:second_start]),
                    int(stamp[second_start:second_start + 2] or 0),
                )
            except ValueError:
                continue
        return None

    def _extract_image(self, article_soup, source: NewsSource) -> str | None:
        if not source.image_selector:
            return None
        image_elem = article_soup.select_one(source.image_selector)
        if not image_elem:
            return None
        image_url = self._extract_image_url_from_element(image_elem)
        if not image_url:
            return None

        image_url = urljoin(source.url, image_url)
        return None if self._is_non_article_image(image_url) else image_url

    def _extract_image_url_from_element(self, image_elem) -> str | None:
        if image_elem.name == "meta":
            return image_elem.get("content")

        for attr in ("data-srcset", "srcset"):
            srcset = image_elem.get(attr)
            if srcset:
                return srcset.split(",")[0].strip().split()[0]

        return (
            image_elem.get("data-src")
            or image_elem.get("data-lazy-src")
            or image_elem.get("src")
        )

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
                return self._clean_text(cat_elem.get_text(" ", strip=True))
        return source.category

    def _parse_date(self, date_text: str, *, fallback_to_now: bool = True) -> datetime | None:
        if not date_text:
            return datetime.now() if fallback_to_now else None

        from dateutil import parser

        date_text = date_text.lower()
        date_text = re.sub(r"hace \d+ horas?", "", date_text)
        date_text = re.sub(r"ayer", "1 day ago", date_text)
        date_text = re.sub(r"hoy", "", date_text)
        date_text = self._normalize_spanish_date_text(date_text)
        timestamp_date = self._parse_numeric_timestamp(date_text)
        if timestamp_date:
            return timestamp_date

        try:
            return parser.parse(
                date_text,
                fuzzy=True,
                dayfirst=self._should_parse_dayfirst(date_text),
            )
        except Exception:
            return datetime.now() if fallback_to_now else None

    def _should_parse_dayfirst(self, date_text: str) -> bool:
        return bool(re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", date_text))

    def _parse_numeric_timestamp(self, date_text: str) -> datetime | None:
        if not re.fullmatch(r"\d{10}|\d{13}", date_text.strip()):
            return None

        timestamp = int(date_text)
        if len(date_text.strip()) == 13:
            timestamp = timestamp / 1000

        try:
            return datetime.fromtimestamp(timestamp)
        except (OSError, OverflowError, ValueError):
            return None

    def _normalize_spanish_date_text(self, date_text: str) -> str:
        month_numbers = {
            "enero": "01",
            "febrero": "02",
            "marzo": "03",
            "abril": "04",
            "mayo": "05",
            "junio": "06",
            "julio": "07",
            "agosto": "08",
            "septiembre": "09",
            "setiembre": "09",
            "octubre": "10",
            "noviembre": "11",
            "diciembre": "12",
        }
        month_pattern = "|".join(month_numbers)

        def replace_day_first(match):
            day = match.group("day")
            month = month_numbers[match.group("month")]
            year = match.group("year")
            time_text = match.group("time") or ""
            return f"{day}/{month}/{year}{time_text}"

        normalized = re.sub(
            rf"(?P<day>\d{{1,2}})\s*(?:de\s+)?(?P<month>{month_pattern})\s*(?:de\s+)?(?P<year>\d{{4}})(?P<time>\s+\d{{1,2}}:\d{{2}})?",
            replace_day_first,
            date_text,
        )

        def replace_month_first(match):
            day = match.group("day")
            month = month_numbers[match.group("month")]
            year = match.group("year")
            time_text = match.group("time") or ""
            return f"{day}/{month}/{year}{time_text}"

        return re.sub(
            rf"(?P<month>{month_pattern})\s+(?P<day>\d{{1,2}}),?\s*(?:de\s+)?(?P<year>\d{{4}})(?P<time>\s+\d{{1,2}}:\d{{2}})?",
            replace_month_first,
            normalized,
        )

    def _extract_json_ld_dates(self, soup: BeautifulSoup) -> list[str]:
        dates = []
        for script in soup.select("script[type='application/ld+json']"):
            raw_json = script.string or script.get_text(strip=True)
            if not raw_json:
                continue
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                continue

            for node in self._iter_json_ld_nodes(data):
                for field in ("datePublished", "dateCreated", "dateModified"):
                    value = node.get(field)
                    if value:
                        dates.append(str(value))
        return dates

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
