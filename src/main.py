from __future__ import annotations

import asyncio
import sys
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from loguru import logger

from src.api import create_economic_indicators_router
from src.collectors import NewsAPICollector, NewsScraper
from src.config import Settings, get_settings
from src.db import Database
from src.distributors import TelegramHandler, WhatsAppHandler
from src.llm import LLMProvider
from src.processors import Deduplicator, NewsClassifier, NewsRanker, NewsRewriter, NewsSummarizer
from src.scheduler import NewsScheduler


class NewsSummarizerApp:
    """Main News Summarizer application."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db: Database | None = None
        self.llm: LLMProvider | None = None
        self.whatsapp: WhatsAppHandler | None = None
        self.telegram: TelegramHandler | None = None
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

        if self.settings.llm_api_key:
            try:
                self.llm = LLMProvider(
                    provider=self.settings.llm_provider,
                    api_key=self.settings.llm_api_key,
                )
                logger.info(f"LLM Provider: {self.llm}")
            except Exception as e:
                logger.error(f"Error inicializando LLM: {e}")
                raise
        else:
            logger.warning("No hay LLM API key configurada!")

        self.whatsapp = WhatsAppHandler(self.db, self.settings)
        self.telegram = TelegramHandler(self.db, self.settings)

        logger.info("Aplicacion iniciada")

    async def shutdown(self):
        """Closes the application."""

        if self.llm:
            await self.llm.close()

        if self.db:
            await self.db.close()

        logger.info("Aplicacion cerrada")

    async def send_summaries(self, time_of_day: str = "morning", refresh: bool = False):
        """Generates and sends summaries to active subscribers."""

        logger.info(f"Generating summaries ({time_of_day}) refresh={refresh}")

        categories = self.settings.categories_list
        sent_count = 0
        news: list[dict] = []
        summaries: list[dict] = []
        used_cached_articles = False
        used_cached_summaries = False
        collection_stats = {"scraper": 0, "newsapi": 0, "inserted": 0, "updated": 0}
        collection_run_id: int | None = None
        collected_fresh_articles = False

        if self.db:
            try:
                summaries = await self.db.get_recent_summaries(categories)
                if summaries and not refresh:
                    used_cached_summaries = True
                    logger.info(f"Reusing {len(summaries)} cached summaries")
                else:
                    since = datetime.utcnow() - timedelta(
                        minutes=self.settings.news_cache_ttl_minutes
                    )
                    news = await self.db.get_recent_articles(categories, since=since, limit=200)
                    if len(news) >= self.settings.news_min_articles and not refresh:
                        used_cached_articles = True
                        logger.info(f"Reusing {len(news)} cached articles")
                    else:
                        news, collection_stats, collection_run_id = await self._collect_news(categories)
                        collected_fresh_articles = True
            except Exception as e:
                logger.error(f"Cache/DB error: {e}")

        if not used_cached_summaries:
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
                    )
                return {
                    "collected": 0,
                    "summaries": len(summaries),
                    "sent": 0,
                    "used_cached_articles": used_cached_articles,
                    "used_cached_summaries": used_cached_summaries,
                    "collection_stats": collection_stats,
                }

            deduplicator = Deduplicator()
            news = deduplicator.deduplicate(news)

            classifier = NewsClassifier(self.llm)
            news = classifier.classify_batch(news)

            ranker = NewsRanker()
            news = ranker.rank(news)

            if self.db and collected_fresh_articles:
                try:
                    db_stats = await self.db.upsert_articles(news)
                    collection_stats["inserted"] += db_stats["inserted"]
                    collection_stats["updated"] += db_stats["updated"]
                except Exception as e:
                    if collection_run_id is not None:
                        await self.db.finish_collection_run(
                            collection_run_id,
                            status="failed",
                            scraper_count=collection_stats["scraper"],
                            newsapi_count=collection_stats["newsapi"],
                            inserted_count=collection_stats["inserted"],
                            updated_count=collection_stats["updated"],
                            error_message=str(e),
                        )
                    raise

            news = news[:20]

            if self.db and collection_run_id is not None:
                await self.db.finish_collection_run(
                    collection_run_id,
                    status="success" if news else "partial",
                    scraper_count=collection_stats["scraper"],
                    newsapi_count=collection_stats["newsapi"],
                    inserted_count=collection_stats["inserted"],
                    updated_count=collection_stats["updated"],
                )

            if not self.llm:
                logger.error("No hay LLM para resumir")
                return {
                    "collected": len(news),
                    "summaries": 0,
                    "sent": 0,
                    "used_cached_articles": used_cached_articles,
                    "used_cached_summaries": used_cached_summaries,
                    "collection_stats": collection_stats,
                }

            summaries = await self._build_summaries(news, categories)

            if summaries:
                rewriter = NewsRewriter(self.llm)
                try:
                    summaries = await rewriter.rewrite(summaries)
                except Exception as e:
                    logger.warning(f"Error reescribiendo: {e}")

            if self.db and summaries:
                try:
                    await self.db.save_summaries(
                        summaries,
                        llm_provider=self.llm.provider,
                        llm_model=self.llm.models.get("quality"),
                    )
                except Exception as e:
                    logger.error(f"Error guardando summaries: {e}")

        if not self.db:
            logger.warning("DB no disponible, no se envia nada")
            return {
                "collected": len(news),
                "summaries": len(summaries),
                "sent": 0,
                "used_cached_articles": used_cached_articles,
                "used_cached_summaries": used_cached_summaries,
                "collection_stats": collection_stats,
            }

        logger.info(f"Checking subscribers... DB: {self.db}")
        try:
            subscribers = await self.db.get_active_subscribers()
        except Exception as e:
            logger.error(f"Error obtaining subscribers: {e}")
            return {
                "collected": len(news),
                "summaries": len(summaries),
                "sent": 0,
                "used_cached_articles": used_cached_articles,
                "used_cached_summaries": used_cached_summaries,
                "collection_stats": collection_stats,
            }

        logger.info(f"Active subscribers: {len(subscribers)}")

        for sub in subscribers:
            try:
                user_categories = sub.categories or categories
                user_news = [n for n in summaries if n.get("category") in user_categories]

                if not user_news:
                    continue

                message = self._format_summary(user_news[:10])

                if sub.channel == "whatsapp" and sub.phone:
                    self.whatsapp.send_message(sub.phone, message)
                    sent_count += 1
                elif sub.channel == "telegram" and sub.telegram_id:
                    await self.telegram.send_message(sub.telegram_id, message)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Error enviando a {sub}: {e}")

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
        }

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
            try:
                cat_summaries = await summarizer.summarize(category_news[:5], category)
                summaries.extend(cat_summaries)
            except Exception as e:
                logger.error(f"Error resumiendo {category}: {e}")

        return summaries

    def _format_summary(self, news: list[dict]) -> str:
        """Formats the summary for delivery."""

        text = "Resumen de Hoy - Bolivia\n\n"

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
app.include_router(create_economic_indicators_router(lambda: app_instance))


@app.get("/")
async def root():
    return {"name": "News Summarizer Bolivia", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(sender: str = None, body: str = None):
    """Webhook for WhatsApp via Twilio."""

    if not app_instance or not app_instance.whatsapp:
        raise HTTPException(status_code=500, detail="WhatsApp no configurado")

    response = app_instance.whatsapp.handle_message(sender, body)
    return {"message": response}


@app.post("/trigger/summary")
async def trigger_summary(time_of_day: str = "manual", refresh: bool = False):
    """Endpoint to trigger the summary manually."""

    if not app_instance:
        raise HTTPException(status_code=500, detail="App no inicializada")

    try:
        result = await app_instance.send_summaries(time_of_day, refresh=refresh)
        return {
            "status": "success",
            "message": f"Resumen {time_of_day} procesado",
            "result": result,
        }
    except Exception as e:
        logger.error(f"Error-trigger: {e}")
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
