from __future__ import annotations

import asyncio
import html
import sys
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api import (
    create_articles_router,
    create_economic_indicators_router,
    create_impact_metrics_router,
    create_preferences_router,
    create_sources_router,
    create_summaries_router,
    create_weather_router,
    create_worldcup_router,
)
from src.api.security import require_cron_key
from src.collectors import NewsAPICollector, NewsScraper
from src.config import Settings, get_settings
from src.db import Database
from src.distributors import EmailHandler, TelegramHandler, WhatsAppHandler
from src.llm import LLMRouter
from src.processors import (
    AIStoryDeduplicator,
    Deduplicator,
    NewsClassifier,
    NewsRanker,
    NewsRewriter,
    NewsSummarizer,
)
from src.scheduler import NewsScheduler

tz_bolivia = ZoneInfo("America/La_Paz")


class NewsSummarizerApp:
    """Main News Summarizer application."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db: Database | None = None
        self.llm: LLMRouter | None = None
        self.whatsapp: WhatsAppHandler | None = None
        self.telegram: TelegramHandler | None = None
        self.email: EmailHandler | None = None
        self.scheduler: NewsScheduler | None = None

    async def startup(self):
        """Initializes the application."""

        logger.remove()
        logger.add(
            sys.stderr,
            level=self.settings.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        )

        if self.settings.is_production:
            log_file = Path("logs")
            log_file.mkdir(exist_ok=True)
            logger.add(
                "logs/{time}.log",
                rotation="1 day",
                retention="7 days",
                level=self.settings.log_level,
            )

        logger.info("=" * 50)
        logger.info("News Summarizer Bolivia - Iniciando")
        logger.info("=" * 50)

        if self.settings.is_production:
            logger.info("Modo produccion")

        try:
            self.db = Database(
                self.settings.database_url,
                pool_size=self.settings.database_pool_size,
                max_overflow=self.settings.database_max_overflow,
            )
            await self.db.init_db()
        except Exception as e:
            logger.warning(f"DB no disponible: {e}. Continuando sin DB.")

        if self.settings.llm_providers_list:
            try:
                self.llm = LLMRouter(
                    providers=self.settings.llm_providers_list,
                )
                logger.info(f"LLM Router: {self.llm}")
            except Exception as e:
                logger.error(f"Error inicializando LLM: {e}")
                raise
        else:
            logger.warning("No hay LLM API key configurada!")

        self.whatsapp = WhatsAppHandler(self.db, self.settings)
        self.telegram = TelegramHandler(self.db, self.settings)
        self.email = EmailHandler(self.db, self.settings)

        logger.info("Aplicacion iniciada")

    async def shutdown(self):
        """Closes the application."""

        if self.llm:
            await self.llm.close()

        if self.db:
            await self.db.close()

        logger.info("Aplicacion cerrada")

    async def send_summaries(
        self,
        time_of_day: str = "morning",
        refresh: bool = False,
        *,
        deliver: bool = True,
    ):
        """Generates summaries and optionally delivers them to active subscribers."""

        logger.info(f"Generating summaries ({time_of_day}) refresh={refresh} deliver={deliver}")
        if self.llm:
            self.llm.reset()

        categories = self.settings.categories_list
        brief_date = self._brief_date()
        sent_count = 0
        delivery_stats = self._empty_delivery_stats()
        news: list[dict] = []
        summaries: list[dict] = []
        used_cached_articles = False
        used_cached_summaries = False
        collection_stats = {"scraper": 0, "newsapi": 0, "inserted": 0, "updated": 0}
        collection_run_id: int | None = None
        collected_fresh_articles = False
        pipeline_metrics: dict[str, Any] = {
            "raw_collected_count": 0,
            "usable_count": 0,
            "quality_dropped_count": 0,
            "deduplicated_count": 0,
            "duplicate_dropped_count": 0,
            "ranked_count": 0,
            "summary_candidates_count": 0,
            "summaries_count": 0,
            "used_cached_articles": False,
            "used_cached_summaries": False,
            "metrics_payload": {},
        }

        if self.db:
            try:
                summaries = await self.db.get_recent_summaries(
                    categories,
                    summary_date=brief_date,
                )
                if summaries and not refresh:
                    used_cached_summaries = True
                    pipeline_metrics["used_cached_summaries"] = True
                    pipeline_metrics["summaries_count"] = len(summaries)
                    logger.info(f"Reusing {len(summaries)} cached summaries")
                else:
                    now_bolivia = datetime.now(tz_bolivia).replace(tzinfo=None)
                    since = now_bolivia - timedelta(
                        minutes=self.settings.news_cache_ttl_minutes
                    )
                    news = await self.db.get_recent_articles(categories, since=since, limit=200)
                    if len(news) >= self.settings.news_min_articles and not refresh:
                        used_cached_articles = True
                        pipeline_metrics["used_cached_articles"] = True
                        pipeline_metrics["usable_count"] = len(news)
                        pipeline_metrics["deduplicated_count"] = len(news)
                        pipeline_metrics["ranked_count"] = len(news)
                        logger.info(f"Reusing {len(news)} cached articles")
                    else:
                        news, collection_stats, collection_run_id = await self._collect_news(categories)
                        collected_fresh_articles = True
                        pipeline_metrics["raw_collected_count"] = len(news)
            except Exception as e:
                logger.error(f"Cache/DB error: {e}")
                pipeline_metrics["metrics_payload"] = {
                    **dict(pipeline_metrics.get("metrics_payload") or {}),
                    "cache_db_error": str(e),
                }
                if not used_cached_summaries and not news:
                    news, collection_stats, collection_run_id = await self._collect_news(categories)
                    collected_fresh_articles = True
                    pipeline_metrics["raw_collected_count"] = len(news)

        if not used_cached_summaries:
            for n in news:
                pa = n.get("published_at")
                if isinstance(pa, datetime) and pa.tzinfo is not None:
                    n["published_at"] = pa.astimezone(tz_bolivia).replace(tzinfo=None)

            today = self._brief_date()
            bolivia_midnight = datetime(today.year, today.month, today.day)
            before_date_filter = len(news)
            news = [
                n for n in news
                if n.get("published_at") is not None
                and n["published_at"] >= bolivia_midnight
            ]
            dropped_date = before_date_filter - len(news)
            if dropped_date:
                logger.info(f"Filtradas {dropped_date} noticias con fecha de publicacion antigua")

            if not news:
                logger.warning("No hay noticias para procesar")
                if self.db and collection_run_id is not None:
                    await self.db.finish_collection_run(
                        collection_run_id,
                        status="partial",
                        scraper_count=collection_stats["scraper"],
                        newsapi_count=collection_stats["newsapi"],
                        inserted_count=collection_stats["inserted"],
                        updated_count=collection_stats["updated"],
                        **pipeline_metrics,
                    )
                return {
                    "collected": 0,
                    "summaries": len(summaries),
                    "sent": 0,
                    "used_cached_articles": used_cached_articles,
                    "used_cached_summaries": used_cached_summaries,
                    "collection_stats": collection_stats,
                    "delivery_stats": delivery_stats,
                }

            before_quality_filter = len(news)
            news = self._filter_usable_articles(news)
            dropped = before_quality_filter - len(news)
            pipeline_metrics["raw_collected_count"] = max(
                int(pipeline_metrics["raw_collected_count"] or 0),
                before_quality_filter,
            )
            pipeline_metrics["usable_count"] = len(news)
            pipeline_metrics["quality_dropped_count"] = dropped
            if dropped:
                logger.info(f"Filtradas {dropped} noticias sin contenido util")

            if not news:
                logger.warning("No hay noticias con contenido util para procesar")
                if self.db and collection_run_id is not None:
                    await self.db.finish_collection_run(
                        collection_run_id,
                        status="partial",
                        scraper_count=collection_stats["scraper"],
                        newsapi_count=collection_stats["newsapi"],
                        inserted_count=collection_stats["inserted"],
                        updated_count=collection_stats["updated"],
                        **pipeline_metrics,
                    )
                return {
                    "collected": 0,
                    "summaries": 0,
                    "sent": 0,
                    "used_cached_articles": used_cached_articles,
                    "used_cached_summaries": used_cached_summaries,
                    "collection_stats": collection_stats,
                    "delivery_stats": delivery_stats,
                }

            deduplicator = Deduplicator()
            before_dedup = len(news)
            news = deduplicator.deduplicate(news)
            pipeline_metrics["deduplicated_count"] = len(news)
            pipeline_metrics["duplicate_dropped_count"] = before_dedup - len(news)

            classifier = NewsClassifier(self.llm)
            news = await classifier.classify_batch_async(news)

            ranker = NewsRanker()
            news = ranker.rank(news)
            pipeline_metrics["ranked_count"] = len(news)

            if self.db and collected_fresh_articles:
                try:
                    db_stats = await self.db.upsert_articles(news)
                    collection_stats["inserted"] += db_stats["inserted"]
                    collection_stats["updated"] += db_stats["updated"]
                    pipeline_metrics["metrics_payload"] = {
                        **dict(pipeline_metrics.get("metrics_payload") or {}),
                        "historical_duplicates_detected": db_stats.get(
                            "historical_duplicates", 0
                        ),
                    }
                except Exception as e:
                    if collection_run_id is not None:
                        await self.db.finish_collection_run(
                            collection_run_id,
                            status="failed",
                            scraper_count=collection_stats["scraper"],
                            newsapi_count=collection_stats["newsapi"],
                            inserted_count=collection_stats["inserted"],
                            updated_count=collection_stats["updated"],
                            **pipeline_metrics,
                            error_message=str(e),
                        )
                    raise

            if not self.llm:
                logger.error("No hay LLM para resumir")
                if self.db and collection_run_id is not None:
                    await self.db.finish_collection_run(
                        collection_run_id,
                        status="partial",
                        scraper_count=collection_stats["scraper"],
                        newsapi_count=collection_stats["newsapi"],
                        inserted_count=collection_stats["inserted"],
                        updated_count=collection_stats["updated"],
                        **pipeline_metrics,
                    )
                return {
                    "collected": len(news),
                    "summaries": 0,
                    "sent": 0,
                    "used_cached_articles": used_cached_articles,
                    "used_cached_summaries": used_cached_summaries,
                    "collection_stats": collection_stats,
                    "delivery_stats": delivery_stats,
                }

            before_dedup = len(news)
            news = [n for n in news if n.get("published_at") is not None]
            if len(news) < before_dedup:
                logger.info(f"Filtradas {before_dedup - len(news)} noticias sin fecha de publicacion")

            already_summarized_removed = 0
            if self.db:
                try:
                    article_ids = [n["id"] for n in news if n.get("id")]
                    summarized_ids = await self.db.get_article_ids_with_summaries(article_ids)
                    if summarized_ids:
                        before = len(news)
                        already_summarized = [n for n in news if n.get("id") in summarized_ids]
                        news = [n for n in news if n.get("id") not in summarized_ids]
                        already_summarized_removed = before - len(news)
                        for a in already_summarized[:10]:
                            logger.info(
                                "  ya resumida  | id={:<5} cat={:<14} score={:<6} title={}",
                                a.get("id"), a.get("category",""), a.get("score",""),
                                (a.get("title","") or "")[:100],
                            )
                        if len(already_summarized) > 10:
                            logger.info("  ... y {} mas ya resumidas", len(already_summarized) - 10)
                        logger.info(f"Filtradas {already_summarized_removed} noticias ya resumidas")
                except Exception as e:
                    logger.warning(f"Error al filtrar noticias ya resumidas: {e}")

            summary_candidates = self._select_summary_candidates(news, categories)
            pipeline_metrics["summary_candidates_count"] = len(summary_candidates)
            for a in summary_candidates:
                logger.info(
                    "  candidato       | id={:<5} cat={:<14} score={:<6} source={:<12} title={}",
                    a.get("id"), a.get("category",""), a.get("score",""),
                    a.get("source","")[:12], (a.get("title","") or "")[:100],
                )
            logger.info(f"Candidatos a resumir: {len(summary_candidates)}")

            llm_dedup_removed = 0
            if summaries and summary_candidates:
                story_deduplicator = AIStoryDeduplicator(self.llm)
                deduped: list[dict] = []
                for cat in categories:
                    cat_articles = [a for a in summary_candidates if a.get("category") == cat]
                    if cat_articles:
                        cat_existing = [s for s in summaries if s.get("category") == cat]
                        before_cat = len(cat_articles)
                        cat_deduped = await story_deduplicator.deduplicate(cat_articles, existing_summaries=cat_existing)
                        cat_removed = before_cat - len(cat_deduped)
                        if cat_removed:
                            removed_titles = {
                                (a.get("id"), (a.get("title","") or "")[:80])
                                for a in cat_articles
                                if a not in cat_deduped
                            }
                            for rid, rtitle in removed_titles:
                                logger.info("  AI dedup descarta | id={:<5} cat={:<14} title={}", rid, cat, rtitle)
                            kept_titles = {
                                (a.get("id"), (a.get("title","") or "")[:80])
                                for a in cat_deduped
                            }
                            for kid, ktitle in kept_titles:
                                logger.info("  AI dedup conserva | id={:<5} cat={:<14} title={}", kid, cat, ktitle)
                        deduped.extend(cat_deduped)
                llm_dedup_removed = len(summary_candidates) - len(deduped)
                summary_candidates = deduped
                pipeline_metrics["ai_dedup_count"] = len(summary_candidates)
                if llm_dedup_removed:
                    logger.info(f"AI dedup elimino {llm_dedup_removed} articulos redundantes, quedan {len(summary_candidates)}")

            logger.info(
                "Dedup metrics: {} ya resumidas, {} por AI dedup, {} candidatos finales",
                already_summarized_removed,
                llm_dedup_removed,
                len(summary_candidates),
            )

            summaries = await self._build_summaries(summary_candidates, categories)

            if summaries:
                rewriter = NewsRewriter(self.llm)
                try:
                    summaries = await rewriter.rewrite(summaries)
                except Exception as e:
                    logger.warning(f"Error reescribiendo: {e}")
            summaries = self._deduplicate_summaries_for_storage(summaries)
            pipeline_metrics["summaries_count"] = len(summaries)

            if self.db and summaries:
                try:
                    await self.db.save_summaries(
                        summaries,
                        llm_provider=self.llm.provider,
                        llm_model=self.llm.models.get("quality"),
                        summary_date=brief_date,
                    )
                except Exception as e:
                    logger.error(f"Error guardando summaries: {e}")

            if self.db and collection_run_id is not None:
                await self.db.finish_collection_run(
                    collection_run_id,
                    status="success" if news else "partial",
                    scraper_count=collection_stats["scraper"],
                    newsapi_count=collection_stats["newsapi"],
                    inserted_count=collection_stats["inserted"],
                    updated_count=collection_stats["updated"],
                    **pipeline_metrics,
                )

        if not self.db:
            logger.warning("DB no disponible, no se envia nada")
            return {
                "collected": len(news),
                "summaries": len(summaries),
                "sent": 0,
                "used_cached_articles": used_cached_articles,
                "used_cached_summaries": used_cached_summaries,
                "collection_stats": collection_stats,
                "delivery_stats": delivery_stats,
            }

        if deliver:
            sent_count, delivery_stats = await self._deliver_summaries(
                summaries=summaries,
                categories=categories,
                time_of_day=time_of_day,
            )
        else:
            logger.info("Delivery skipped for summary refresh")

        logger.info(f"Resumenes procesados: {len(summaries)}")
        if summaries:
            logger.info(f"Sample summary: {summaries[0]}")

        return {
            "collected": len(news),
            "summaries": len(summaries),
            "sent": sent_count,
            "used_cached_articles": used_cached_articles,
            "used_cached_summaries": used_cached_summaries,
            "collection_stats": collection_stats,
            "delivery_stats": delivery_stats,
        }

    async def deliver_cached_summaries(self, time_of_day: str = "manual"):
        """Entrega summaries ya guardados sin recolectar, deduplicar ni llamar al LLM."""

        categories = self.settings.categories_list
        brief_date = self._brief_date()
        if not self.db:
            logger.warning("DB no disponible, no se entregan summaries cacheados")
            return {
                "collected": 0,
                "summaries": 0,
                "sent": 0,
                "used_cached_articles": False,
                "used_cached_summaries": False,
                "collection_stats": {"scraper": 0, "newsapi": 0, "inserted": 0, "updated": 0},
                "delivery_stats": self._empty_delivery_stats(),
            }

        summaries = await self.db.get_recent_summaries(categories, summary_date=brief_date)
        sent_count, delivery_stats = await self._deliver_summaries(
            summaries=summaries,
            categories=categories,
            time_of_day=time_of_day,
        )
        return {
            "collected": 0,
            "summaries": len(summaries),
            "sent": sent_count,
            "used_cached_articles": False,
            "used_cached_summaries": bool(summaries),
            "collection_stats": {"scraper": 0, "newsapi": 0, "inserted": 0, "updated": 0},
            "delivery_stats": delivery_stats,
        }

    async def _deliver_summaries(
        self,
        *,
        summaries: list[dict],
        categories: list[str],
        time_of_day: str,
    ) -> tuple[int, dict[str, dict[str, int]]]:
        if not self.db:
            logger.warning("DB no disponible, no se envia nada")
            return 0, self._empty_delivery_stats()

        sent_count = 0
        delivery_stats = self._empty_delivery_stats()

        logger.info(f"Checking subscribers... DB: {self.db}")
        try:
            subscribers = await self.db.get_active_subscribers()
        except Exception as e:
            logger.error(f"Error obtaining subscribers: {e}")
            return 0, delivery_stats

        logger.info(f"Active subscribers: {len(subscribers)}")

        for sub in subscribers:
            try:
                if not self._should_send_to_subscriber(sub, time_of_day):
                    logger.info(
                        "Skipping subscriber outside preferences: "
                        f"channel={getattr(sub, 'channel', None)} "
                        f"preferred_time={getattr(sub, 'preferred_time', None)} "
                        f"frequency={getattr(sub, 'frequency', None)}"
                    )
                    continue

                user_categories = sub.categories or categories
                user_news = [n for n in summaries if n.get("category") in user_categories]
                user_news = self._deduplicate_summaries_for_delivery(user_news)

                if not user_news:
                    continue

                user_news = user_news[:10]

                if sub.channel == "whatsapp" and sub.phone:
                    message = self._format_summary(user_news)
                    delivered = bool(self.whatsapp and self.whatsapp.send_message(sub.phone, message))
                    if delivered:
                        sent_count += 1
                        delivery_stats["sent_by_channel"]["whatsapp"] += 1
                    else:
                        delivery_stats["failed_by_channel"]["whatsapp"] += 1
                elif sub.channel == "telegram" and sub.telegram_id:
                    message = self._format_summary(user_news)
                    delivered = bool(
                        self.telegram and await self.telegram.send_message(sub.telegram_id, message)
                    )
                    if delivered:
                        sent_count += 1
                        delivery_stats["sent_by_channel"]["telegram"] += 1
                    else:
                        delivery_stats["failed_by_channel"]["telegram"] += 1
                elif sub.channel == "email" and getattr(sub, "email", None):
                    subject, body, html_body = self._format_email_summary(user_news)
                    delivered = bool(
                        self.email
                        and await self.email.send_message(
                            sub.email,
                            subject,
                            body,
                            html_body,
                        )
                    )
                    if delivered:
                        sent_count += 1
                        delivery_stats["sent_by_channel"]["email"] += 1
                    else:
                        delivery_stats["failed_by_channel"]["email"] += 1
            except Exception as e:
                logger.error(f"Error enviando a {sub}: {e}")

        return sent_count, delivery_stats

    def _empty_delivery_stats(self) -> dict[str, dict[str, int]]:
        return {
            "sent_by_channel": {"email": 0, "telegram": 0, "whatsapp": 0},
            "failed_by_channel": {"email": 0, "telegram": 0, "whatsapp": 0},
        }

    def _filter_usable_articles(self, news: list[dict]) -> list[dict]:
        return [article for article in news if self._has_usable_article_text(article)]

    def _has_usable_article_text(self, article: dict) -> bool:
        text = " ".join(
            str(article.get(field) or "")
            for field in ("description", "content", "excerpt")
        ).strip()
        if not text:
            return False

        title = str(article.get("title") or "").strip().lower()
        normalized_text = " ".join(text.lower().split())
        normalized_title = " ".join(title.split())
        if normalized_text == normalized_title:
            return False

        return len(normalized_text) >= 50 or len(normalized_text.split()) >= 8

    async def _collect_news(
        self, categories: list[str]
    ) -> tuple[list[dict], dict[str, int], int | None]:
        news: list[dict] = []
        stats = {"scraper": 0, "newsapi": 0, "inserted": 0, "updated": 0}
        run_id: int | None = None

        if self.db:
            try:
                run_id = await self.db.start_collection_run(categories)
            except Exception as e:
                logger.warning(f"No se pudo crear collection_run: {e}")

        try:
            if self.settings.scraper_enabled:
                try:
                    scraper = NewsScraper(
                        user_agent=self.settings.scraper_user_agent,
                        timeout=self.settings.scraper_timeout,
                        config_path=self.settings.scraper_config_path,
                        timezone=self.settings.schedule_timezone,
                    )
                    scraped = await scraper.fetch_all(categories=categories)
                    news.extend(scraped)
                    stats["scraper"] = len(scraped)
                    logger.info(f"Scraped {len(scraped)} noticias")
                    logger.info(f"News sample: {scraped[:2]}")
                except Exception as e:
                    logger.error(f"Error en scraper: {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")

            if self.settings.news_api_key:
                try:
                    newsapi = NewsAPICollector(
                        api_key=self.settings.news_api_key,
                        country=self.settings.news_api_country,
                        language=self.settings.news_api_language,
                    )
                    api_news = await newsapi.fetch(categories=categories)
                    news.extend(api_news)
                    stats["newsapi"] = len(api_news)
                    logger.info(f"NewsAPI {len(api_news)} noticias")
                except Exception as e:
                    logger.error(f"Error en NewsAPI: {e}")

            logger.info(f"Total news collected: {len(news)}")

            return news, stats, run_id
        except Exception as e:
            if self.db and run_id is not None:
                try:
                    await self.db.finish_collection_run(
                        run_id,
                        status="failed",
                        scraper_count=stats["scraper"],
                        newsapi_count=stats["newsapi"],
                        inserted_count=stats["inserted"],
                        updated_count=stats["updated"],
                        error_message=str(e),
                    )
                except Exception as inner_error:
                    logger.warning(f"No se pudo cerrar collection_run: {inner_error}")
            raise

    async def _build_summaries(self, news: list[dict], categories: list[str]) -> list[dict]:
        summarizer = NewsSummarizer(self.llm)
        summaries: list[dict] = []

        for category in categories:
            category_news = [n for n in news if n.get("category") == category]
            if not category_news:
                continue
            cat_limit = self._per_category_limit(category)
            to_summarize = category_news[:cat_limit]
            if len(category_news) > 5:
                        logger.info(
                            "  categoria {:<14} | {} candidatos, limitado a {} (descarta {} con menor score)",
                            category, len(category_news), cat_limit, len(category_news) - cat_limit,
                        )
            for a in to_summarize:
                logger.info(
                    "  a resumir       | id={:<5} cat={:<14} score={:<6} title={}",
                    a.get("id"), a.get("category",""), a.get("score",""),
                    (a.get("title","") or "")[:100],
                )
            try:
                cat_summaries = await summarizer.summarize(to_summarize, category)
                logger.info(
                    "  categoria {:<14} | {} enviados, {} resumenes generados",
                    category, len(to_summarize), len(cat_summaries),
                )
                summaries.extend(cat_summaries)
            except Exception as e:
                logger.error(f"Error resumiendo {category}: {e}")

        return summaries

    def _per_category_limit(self, category: str) -> int:
        extended = [
            c.strip().lower()
            for c in self.settings.summary_candidates_extended_categories.split(",")
        ]
        if category.strip().lower() in extended:
            return self.settings.summary_candidates_extended_limit
        return self.settings.summary_candidates_per_category

    def _select_summary_candidates(
        self,
        news: list[dict],
        categories: list[str],
        per_category_limit: int | None = None,
        max_per_source: int = 2,
    ) -> list[dict]:
        selected: list[dict] = []
        selected_ids: set[int] = set()
        news = self._select_unique_story_articles(news)

        for category in categories:
            category_news = [article for article in news if article.get("category") == category]
            category_news.sort(key=lambda a: a.get("score", 0) or 0, reverse=True)
            cat_limit = per_category_limit if per_category_limit is not None else self._per_category_limit(category)
            category_selection = self._select_diverse_articles(
                category_news,
                limit=cat_limit,
                max_per_source=max_per_source,
            )
            for article in category_selection:
                article_key = id(article)
                if article_key not in selected_ids:
                    selected.append(article)
                    selected_ids.add(article_key)

        return selected

    def _select_unique_story_articles(self, articles: list[dict]) -> list[dict]:
        unique: list[dict] = []
        seen_clusters: set[str] = set()

        for article in articles:
            if article.get("duplicate_of_article_id"):
                continue

            cluster_id = str(article.get("story_cluster_id") or article.get("cluster_id") or "").strip()
            if cluster_id:
                if cluster_id in seen_clusters:
                    continue
                seen_clusters.add(cluster_id)

            unique.append(article)

        return unique

    def _select_diverse_articles(
        self,
        articles: list[dict],
        *,
        limit: int,
        max_per_source: int,
    ) -> list[dict]:
        if limit <= 0 or not articles:
            return []

        selected: list[dict] = []
        source_counts: dict[str, int] = {}

        for article in articles:
            source = self._normalize_source_name(article.get("source"))
            if source_counts.get(source, 0) >= max_per_source:
                continue
            selected.append(article)
            source_counts[source] = source_counts.get(source, 0) + 1
            if len(selected) >= limit:
                return selected

        if len(selected) >= limit:
            return selected

        selected_ids = {id(article) for article in selected}
        for article in articles:
            if id(article) in selected_ids:
                continue
            selected.append(article)
            if len(selected) >= limit:
                break

        return selected

    def _normalize_source_name(self, source: object) -> str:
        normalized = str(source or "unknown").strip().lower()
        return normalized or "unknown"

    def _format_summary(self, news: list[dict]) -> str:
        """Formats the summary for delivery."""

        text = "EcoBrief Bolivia - Brief del dia\n\n"
        text += "Noticias locales resumidas con menos ruido.\n\n"

        for i, article in enumerate(news, 1):
            title = article.get("title", "")[:80]
            summary = article.get("summary", "")[:150]

            text += f"{i}. {title}\n"
            text += f"   {summary}\n"

            if article.get("fact"):
                text += f"   Dato: {article.get('fact')}\n"
            text += "\n"

        text += "---\n"
        text += "/preferencias | /cancelar"

        return text

    def _should_send_to_subscriber(self, subscriber: Any, time_of_day: str) -> bool:
        if time_of_day == "manual":
            return True

        if not self._matches_preferred_time(subscriber, time_of_day):
            return False

        return self._matches_frequency(subscriber)

    def _matches_preferred_time(self, subscriber: Any, time_of_day: str) -> bool:
        preferred_time = str(getattr(subscriber, "preferred_time", "manana") or "manana").lower()
        if time_of_day == "morning":
            return preferred_time == "manana"
        if time_of_day == "afternoon":
            return preferred_time == "tarde"
        if time_of_day == "night":
            return preferred_time == "noche"
        if time_of_day == "evening":
            return preferred_time in {"tarde", "noche"}
        return True

    def _format_email_summary(self, news: list[dict]) -> tuple[str, str, str]:
        subject = "EcoBrief Bolivia - Brief del dia"
        body = "EcoBrief Bolivia - Brief del dia\n\n"
        body += "Noticias locales resumidas con menos ruido.\n\n"
        items_html = []

        for index, article in enumerate(news, 1):
            title = str(article.get("title", ""))[:120]
            summary = str(article.get("summary", ""))[:500]
            fact = str(article.get("fact") or "").strip()
            source = str(article.get("source") or "").strip()
            url = str(article.get("url") or "").strip()
            category = str(article.get("category") or "general").strip()

            body += f"{index}. {title}\n"
            body += f"   {summary}\n"

            if fact:
                body += f"   Dato: {fact}\n"
            if source:
                body += f"   Fuente: {source}\n"
            if url:
                body += f"   Link: {url}\n"
            body += "\n"

            meta_parts = []
            if fact:
                meta_parts.append(f"<strong>Dato:</strong> {html.escape(fact)}")
            if source:
                meta_parts.append(f"<strong>Fuente:</strong> {html.escape(source)}")
            if url:
                safe_url = html.escape(url, quote=True)
                meta_parts.append(
                    '<a href="'
                    f'{safe_url}" '
                    'style="color:#00606a;text-decoration:none;font-weight:700;">Link</a>'
                )
            meta_html = " · ".join(meta_parts)

            meta_html = " &middot; ".join(meta_parts)
            source_label = html.escape(source or "EcoBrief Bolivia")
            category_label = html.escape(category)

            items_html.append(
                f"""
                <tr>
                  <td style="padding:8px 0;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#ffffff;border:1px solid rgba(34,34,34,0.12);border-top:4px solid #16a34a;border-radius:8px;">
                      <tr>
                        <td valign="top" width="42" style="padding:14px 0 14px 14px;">
                          <div style="width:28px;height:28px;border-radius:8px;background:#bbf7d0;color:#14532d;font:700 13px Inter,Segoe UI,Arial,sans-serif;text-align:center;line-height:28px;">
                            {index}
                          </div>
                        </td>
                        <td style="padding:14px;">
                          <p style="margin:0 0 6px;color:#666666;font:700 11px/1.3 Inter,Segoe UI,Arial,sans-serif;text-transform:uppercase;letter-spacing:.06em;">
                            {source_label} - {category_label}
                            <span style="display:inline-block;margin-left:8px;border:1px solid rgba(22,163,74,.72);border-radius:999px;padding:3px 7px;background:#bbf7d0;color:#14532d;font:700 10px/1 Inter,Segoe UI,Arial,sans-serif;text-transform:none;letter-spacing:0;">
                              Resumido IA
                            </span>
                          </p>
                          <h2 style="margin:0 0 8px;color:#222222;font:700 19px/1.22 Georgia,'Times New Roman',serif;">
                            {html.escape(title)}
                          </h2>
                          <p style="margin:0 0 10px;color:#3f424c;font:400 14px/1.55 Inter,Segoe UI,Arial,sans-serif;">
                            {html.escape(summary)}
                          </p>
                          <p style="margin:0;color:#666666;font:400 12px/1.55 Inter,Segoe UI,Arial,sans-serif;">
                            {meta_html}
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                """
            )

        body += "---\n"
        body += "Puedes cambiar tus preferencias o darte de baja desde EcoBrief Bolivia.\n"
        html_body = self._format_email_html("".join(items_html))
        return subject, body, html_body

    def _format_email_html(self, items_html: str) -> str:
        return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#fafafa;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#fafafa;padding:24px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:720px;background:#ffffff;border:1px solid rgba(34,34,34,0.12);border-radius:8px;overflow:hidden;">
            <tr>
              <td style="background:#ffffff;border-top:6px solid #16a34a;padding:22px 24px 18px;">
                <p style="margin:0 0 6px;color:#666666;font:700 12px/1.2 Inter,Segoe UI,Arial,sans-serif;text-transform:uppercase;letter-spacing:.08em;">
                  EcoBrief Bolivia
                </p>
                <h1 style="margin:0;color:#222222;font:700 30px/1.12 Georgia,'Times New Roman',serif;">
                  Brief del dia
                </h1>
                <p style="margin:10px 0 0;color:#3f424c;font:400 14px/1.5 Inter,Segoe UI,Arial,sans-serif;">
                  Noticias locales resumidas con menos ruido.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 24px 12px;background:#fafafa;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  {items_html}
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 24px 22px;background:#ffffff;border-top:1px solid rgba(34,34,34,0.12);">
                <p style="margin:0;color:#666666;font:400 12px/1.6 Inter,Segoe UI,Arial,sans-serif;">
                  Puedes cambiar tus preferencias o darte de baja desde EcoBrief Bolivia.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""

    def _matches_frequency(self, subscriber: Any) -> bool:
        frequency = str(getattr(subscriber, "frequency", "diario") or "diario").lower()
        local_date = self._subscriber_local_now(subscriber).date()
        weekday = local_date.weekday()

        if frequency == "diario":
            return True
        if frequency == "dias_habiles":
            return weekday < 5
        if frequency == "tres_veces_semana":
            return weekday in {0, 2, 4}
        if frequency == "semanal":
            return weekday == 0
        return True

    def _subscriber_local_now(self, subscriber: Any) -> datetime:
        timezone_name = str(
            getattr(subscriber, "timezone", None)
            or getattr(self.settings, "schedule_timezone", "America/La_Paz")
            or "America/La_Paz"
        )
        try:
            return datetime.now(ZoneInfo(timezone_name))
        except ZoneInfoNotFoundError:
            return datetime.now(ZoneInfo("America/La_Paz"))

    def _brief_date(self):
        timezone_name = str(
            getattr(self.settings, "schedule_timezone", None)
            or "America/La_Paz"
        )
        try:
            return datetime.now(ZoneInfo(timezone_name)).date()
        except ZoneInfoNotFoundError:
            return datetime.now(ZoneInfo("America/La_Paz")).date()

    def _deduplicate_summaries_for_delivery(self, summaries: list[dict]) -> list[dict]:
        unique: list[dict] = []
        seen: set[str] = set()

        for summary in summaries:
            title_key = self._summary_delivery_key(summary)
            if title_key in seen:
                continue
            seen.add(title_key)
            unique.append(summary)

        return unique

    def _deduplicate_summaries_for_storage(self, summaries: list[dict]) -> list[dict]:
        unique: list[dict] = []
        seen: set[str] = set()
        seen_article_ids: set[int] = set()

        for summary in summaries:
            article_id = summary.get("article_id")
            if article_id is not None:
                article_id = int(article_id)
                if article_id in seen_article_ids:
                    continue
                seen_article_ids.add(article_id)

            category = str(summary.get("category") or "general").strip().lower()
            key = f"{category}:{self._summary_delivery_key(summary)}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(summary)

        return unique

    def _summary_delivery_key(self, summary: dict) -> str:
        story_cluster_id = str(summary.get("story_cluster_id") or "").strip()
        if story_cluster_id:
            return f"cluster:{story_cluster_id}"
        return f"title:{self._summary_title_key(summary.get('title'))}"

    def _summary_title_key(self, title: object) -> str:
        import re
        import unicodedata

        normalized = unicodedata.normalize("NFD", str(title or ""))
        normalized = "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )
        normalized = normalized.lower()
        normalized = re.sub(r"[^\w\s]", "", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def run_sync(self):
        """Executes summary delivery synchronously."""

        return asyncio.run(self.send_summaries())


app_instance: NewsSummarizerApp | None = None
settings: Settings | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global app_instance, settings

    settings = get_settings()
    app_instance = NewsSummarizerApp(settings)

    await app_instance.startup()

    yield

    await app_instance.shutdown()


app = FastAPI(
    title="News Summarizer Bolivia",
    description="Resume noticias diarias de Bolivia",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_economic_indicators_router(lambda: app_instance))
app.include_router(create_weather_router())
app.include_router(create_sources_router())
app.include_router(create_articles_router(lambda: app_instance))
app.include_router(create_summaries_router(lambda: app_instance))
app.include_router(create_impact_metrics_router(lambda: app_instance))
app.include_router(create_preferences_router(lambda: app_instance))
app.include_router(create_worldcup_router(lambda: app_instance))


@app.get("/")
async def root():
    return {"name": "News Summarizer Bolivia", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    status = "healthy"
    db_status = "not_configured"
    categories_count = 0

    if app_instance and app_instance.db:
        try:
            async with app_instance.db.session_maker() as session:
                from sqlalchemy import func, select

                from src.db import NewsCategory
                result = await session.execute(select(func.count(NewsCategory.id)))
                categories_count = result.scalar() or 0
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {e}"
            status = "degraded"

    return {
        "status": status,
        "database": db_status,
        "categories": categories_count,
    }


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(sender: str = None, body: str = None):
    """Webhook for WhatsApp via Twilio."""

    if not app_instance or not app_instance.whatsapp:
        raise HTTPException(status_code=500, detail="WhatsApp no configurado")

    response = app_instance.whatsapp.handle_message(sender, body)
    return {"message": response}


@app.post("/trigger/summary")
async def trigger_summary(
    response: Response,
    time_of_day: str = "manual",
    refresh: bool = False,
    async_mode: bool = False,
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
        description="Clave privada para endpoints internos.",
    ),
):
    """Genera o actualiza summaries. No entrega a suscriptores por defecto."""

    if not app_instance:
        raise HTTPException(status_code=500, detail="App no inicializada")
    await require_cron_key(app_instance, x_api_key)

    if async_mode:
        if not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible para registrar job")

        job_id = str(uuid4())
        job = await app_instance.db.create_summary_refresh_job(
            job_id,
            time_of_day=time_of_day,
            refresh=refresh,
        )
        asyncio.create_task(_run_summary_refresh_job(job_id, time_of_day, refresh))
        response.status_code = 202
        return {
            "status": "accepted",
            "message": "Resumen en proceso",
            "job": job,
            "status_url": f"/trigger/summary/jobs/{job_id}",
        }

    try:
        result = await app_instance.send_summaries(
            time_of_day,
            refresh=refresh,
            deliver=False,
        )
        logger.info(
            "Manual summary refresh completed: "
            f"collected={result.get('collected')} processed={result.get('processed')} "
            f"summaries={result.get('summaries')} sent={result.get('sent')}"
        )
        return {
            "status": "success",
            "message": f"Resumen {time_of_day} procesado",
            "result": result,
        }
    except Exception as e:
        logger.error(f"Error-trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _run_summary_refresh_job(job_id: str, time_of_day: str, refresh: bool) -> None:
    if not app_instance or not app_instance.db:
        return

    try:
        await app_instance.db.mark_summary_refresh_job_running(job_id)
        result = await app_instance.send_summaries(
            time_of_day,
            refresh=refresh,
            deliver=False,
        )
        await app_instance.db.finish_summary_refresh_job(job_id, result)
        logger.info(
            "Async summary refresh completed: "
            f"job_id={job_id} collected={result.get('collected')} "
            f"summaries={result.get('summaries')}"
        )
    except Exception as e:
        logger.error(f"Async summary refresh failed job_id={job_id}: {e}")
        try:
            await app_instance.db.fail_summary_refresh_job(job_id, str(e))
        except Exception as update_error:
            logger.error(f"Error updating failed summary job {job_id}: {update_error}")


@app.get("/trigger/summary/jobs/{job_id}")
async def get_summary_refresh_job(
    job_id: str,
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
        description="Clave privada para endpoints internos.",
    ),
):
    """Consulta el estado de un refresh asincrono."""

    if not app_instance:
        raise HTTPException(status_code=500, detail="App no inicializada")
    await require_cron_key(app_instance, x_api_key)
    if not app_instance.db:
        raise HTTPException(status_code=503, detail="DB no disponible")

    job = await app_instance.db.get_summary_refresh_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    return {"status": job["status"], "job": job}


@app.post("/trigger/delivery")
async def trigger_delivery(
    time_of_day: str = "manual",
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
        description="Clave privada para endpoints internos.",
    ),
):
    """Entrega summaries existentes sin recolectar ni generar nuevos briefs."""

    if not app_instance:
        raise HTTPException(status_code=500, detail="App no inicializada")
    await require_cron_key(app_instance, x_api_key)

    try:
        result = await app_instance.deliver_cached_summaries(time_of_day)
        logger.info(
            "Cached summary delivery completed: "
            f"summaries={result.get('summaries')} sent={result.get('sent')}"
        )
        return {
            "status": "success",
            "message": f"Entrega {time_of_day} procesada",
            "result": result,
        }
    except Exception as e:
        logger.error(f"Error-delivery-trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/stats")
async def get_stats():
    """Returns statistics."""

    if not app_instance or not app_instance.db:
        return {"subscribers": 0}

    try:
        count = await app_instance.db.get_subscription_count()
        return {"subscribers": count}
    except Exception:
        return {"subscribers": 0}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
