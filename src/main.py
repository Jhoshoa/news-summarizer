import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from loguru import logger
import sys

from src.config import Settings, get_settings
from src.llm import LLMProvider
from src.db import Database
from src.collectors import NewsAPICollector, NewsScraper
from src.processors import Deduplicator, NewsClassifier, NewsRanker, NewsSummarizer, NewsRewriter
from src.distributors import WhatsAppHandler, TelegramHandler
from src.scheduler import NewsScheduler


class NewsSummarizerApp:
    """Aplicación principal de News Summarizer."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db: Database = None
        self.llm: LLMProvider = None
        self.whatsapp: WhatsAppHandler = None
        self.telegram: TelegramHandler = None
        self.scheduler: NewsScheduler = None

    async def startup(self):
        """Inicializa la aplicación."""

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
            from gunicorn.app.base import Application

            logger.info("Modo producción")

        try:
            self.db = Database(self.settings.database_url)
            await self.db.init_db()
        except Exception as e:
            logger.warning(f"DB no disponible: {e}. Continuando sin DB.")

        if self.settings.llm_api_key:
            try:
                self.llm = LLMProvider(
                    provider=self.settings.llm_provider, api_key=self.settings.llm_api_key
                )
                logger.info(f"LLM Provider: {self.llm}")
            except Exception as e:
                logger.error(f"Error inicializando LLM: {e}")
                raise
        else:
            logger.warning("No hay LLM API key configurada!")

        self.whatsapp = WhatsAppHandler(self.db, self.settings)

        self.telegram = TelegramHandler(self.db, self.settings)

        logger.info("✅ Aplicación iniciada")

    async def shutdown(self):
        """Cierra la aplicación."""

        if self.llm:
            await self.llm.close()

        if self.db:
            await self.db.close()

        logger.info("🛑 Aplicación cerrada")

    async def send_summaries(self, time_of_day: str = "morning"):
        """Genera y envía resúmenes a todos los subscribers."""

        logger.info(f"Generando resúmenes ({time_of_day})...")

        news = []

        if self.settings.scraper_enabled:
            try:
                scraper = NewsScraper(
                    user_agent=self.settings.scraper_user_agent,
                    timeout=self.settings.scraper_timeout,
                    config_path=self.settings.scraper_config_path,
                )
                print(self.settings.categories_list)
                print(self.settings.scraper_user_agent)
                print(self.settings.scraper_timeout)
                scraped = await scraper.fetch_all(categories=self.settings.categories_list)
                news.extend(scraped)
                print("===================>>>>>>>>>>>>>>>>>>>>>>>>>>")
                print(scraped)
                logger.info(f"Scraped {len(scraped)} noticias")
                logger.info(f"News sample: {scraped[:2]}")
            except Exception as e:
                logger.error(f"Error en scraper: {e}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")

        if self.settings.news_api_key:
            try:
                newsapi = NewsAPICollector(
                    api_key=self.settings.news_api_key,
                    country=self.settings.news_api_country,
                    language=self.settings.news_api_language,
                )
                api_news = await newsapi.fetch(categories=self.settings.categories_list)
                news.extend(api_news)
                logger.info(f"NewsAPI {len(api_news)} noticias")
            except Exception as e:
                logger.error(f"Error en NewsAPI: {e}")

        logger.info(f"Total news collected: {len(news)}")
        if not news:
            logger.warning("No hay noticias para procesar")
            return

        deduplicator = Deduplicator()
        news = deduplicator.deduplicate(news)

        classifier = NewsClassifier(self.llm)
        news = classifier.classify_batch(news)

        ranker = NewsRanker()
        news = ranker.rank(news, limit=20)

        if not self.llm:
            logger.error("No hay LLM para resumir")
            return

        summarizer = NewsSummarizer(self.llm)
        summaries = []

        for category in self.settings.categories_list:
            category_news = [n for n in news if n.get("category") == category]
            if category_news:
                try:
                    cat_summaries = await summarizer.summarize(category_news[:5], category)
                    summaries.extend(cat_summaries)
                except Exception as e:
                    logger.error(f"Error resumiendo {category}: {e}")

        if summaries:
            rewriter = NewsRewriter(self.llm)
            try:
                summaries = await rewriter.rewrite(summaries)
            except Exception as e:
                logger.warning(f"Error reescribiendo: {e}")

        if not self.db:
            logger.warning("DB no disponible, no se envía nada")
            return

        logger.info(f"Checking subscribers... DB: {self.db}")
        try:
            subscribers = await self.db.get_active_subscribers()
        except Exception as e:
            logger.error(f"Error obtaining subscribers: {e}")
            return

        logger.info(f"Active subscribers: {len(subscribers)}")

        for sub in subscribers:
            try:
                user_categories = sub.categories or self.settings.categories_list
                user_news = [n for n in summaries if n.get("category") in user_categories]

                if not user_news:
                    continue

                message = self._format_summary(user_news[:10])

                if sub.channel == "whatsapp" and sub.phone:
                    self.whatsapp.send_message(sub.phone, message)
                elif sub.channel == "telegram" and sub.telegram_id:
                    await self.telegram.send_message(sub.telegram_id, message)
            except Exception as e:
                logger.error(f"Error enviando a {sub}: {e}")

        logger.info(f"Resúmenes procesados: {len(summaries)}")
        if summaries:
            logger.info(f"Sample summary: {summaries[0]}")

    def _format_summary(self, news: list[dict]) -> str:
        """Formatea el resumen para envío."""

        text = "📰 *Resumen de Hoy* 🇧🇴\n\n"

        for i, article in enumerate(news, 1):
            title = article.get("title", "")[:80]
            summary = article.get("summary", "")[:150]

            text += f"{i}. *{title}*\n"
            text += f"   {summary}\n"

            if article.get("fact"):
                text += f"   📌 {article.get('fact')}\n"
            text += "\n"

        text += "---\n"
        text += "📍 /preferencias | /cancelar"

        return text

    def run_sync(self):
        """Ejecuta el envío de resúmenes (sync)."""

        return asyncio.run(self.send_summaries())


app_instance: NewsSummarizerApp = None
settings: Settings = None


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


@app.get("/")
async def root():
    return {"name": "News Summarizer Bolivia", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(sender: str = None, body: str = None):
    """Webhook para WhatsApp via Twilio."""

    if not app_instance or not app_instance.whatsapp:
        raise HTTPException(status_code=500, detail="WhatsApp no configurado")

    response = app_instance.whatsapp.handle_message(sender, body)
    return {"message": response}


@app.post("/trigger/summary")
async def trigger_summary(time_of_day: str = "manual"):
    """Endpoint para activar el resumen manualmente."""

    if not app_instance:
        raise HTTPException(status_code=500, detail="App no inicializada")

    try:
        await app_instance.send_summaries(time_of_day)
        return {"status": "success", "message": f"Resumen {time_of_day} enviado"}
    except Exception as e:
        logger.error(f"Error-trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Obtiene estadísticas."""

    if not app_instance or not app_instance.db:
        return {"subscribers": 0}

    try:
        count = await app_instance.db.get_subscription_count()
        return {"subscribers": count}
    except:
        return {"subscribers": 0}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
