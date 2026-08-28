from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.db.repository import DEFAULT_CATEGORIES

_DEFAULT_CATEGORIES_ENV_VALUE = ",".join(DEFAULT_CATEGORIES)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="DEBUG", alias="LOG_LEVEL")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")

    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    github_api_key: str | None = Field(default=None, alias="GITHUB_API_KEY")
    nvidia_api_key: str | None = Field(default=None, alias="NVIDIA_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    # nvidia va al final (antes de openai, que casi nunca esta configurado):
    # es el fallback mas lento y menos confiable de los que ya probamos en
    # produccion (llamadas de 5+ minutos, a veces cuelga). gemini va segundo,
    # justo despues de groq, porque tiene cuota diaria mas generosa y
    # respuestas mas confiables.
    llm_fallback_order: str = Field(
        default="groq,gemini,github,nvidia,openai", alias="LLM_FALLBACK_ORDER"
    )
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")

    news_api_key: str | None = Field(default=None, alias="NEWS_API_KEY")
    news_api_country: str = Field(default="bo", alias="NEWS_API_COUNTRY")
    news_api_language: str = Field(default="es", alias="NEWS_API_LANGUAGE")

    scraper_enabled: bool = Field(default=True, alias="SCRAPER_ENABLED")
    scraper_concurrency: int = Field(default=3, alias="SCRAPER_CONCURRENCY")
    scraper_timeout: int = Field(default=30, alias="SCRAPER_TIMEOUT")
    scraper_config_path: str | None = Field(
        default="config/sources.yaml", alias="SCRAPER_CONFIG_PATH"
    )
    scraper_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        alias="SCRAPER_USER_AGENT",
    )
    scraper_sources: str = Field(
        default="radiofides,unitel,reduno,redbolivision", alias="SCRAPER_SOURCES"
    )
    # Un articulo ya scrapeado (con contenido guardado) no se vuelve a pedir
    # completo si ya paso este numero de horas desde su publicacion -- antes
    # de eso se sigue re-chequeando por si la nota se actualiza (comun en
    # coberturas "en desarrollo").
    scraper_detail_refresh_hours: int = Field(
        default=3, alias="SCRAPER_DETAIL_REFRESH_HOURS"
    )

    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str | None = Field(default=None, alias="TWILIO_PHONE_NUMBER")
    twilio_webhook_url: str | None = Field(default=None, alias="TWILIO_WEBHOOK_URL")

    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: str | None = Field(default=None, alias="TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: str | None = Field(default=None, alias="TELEGRAM_WEBHOOK_SECRET")

    email_enabled: bool = Field(default=False, alias="EMAIL_ENABLED")
    email_provider: str = Field(default="smtp", alias="EMAIL_PROVIDER")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="EcoBrief Bolivia", alias="SMTP_FROM_NAME")
    email_require_verification: bool = Field(default=False, alias="EMAIL_REQUIRE_VERIFICATION")

    database_url: str = Field(
        default="postgresql+asyncpg://user:pass@localhost:5433/news_summarizer",
        alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    news_cache_ttl_minutes: int = Field(default=60, alias="NEWS_CACHE_TTL_MINUTES")
    news_min_articles: int = Field(default=20, alias="NEWS_MIN_ARTICLES")
    news_summary_retention_days: int = Field(
        default=30, alias="NEWS_SUMMARY_RETENTION_DAYS"
    )

    schedule_timezone: str = Field(default="America/La_Paz", alias="SCHEDULE_TIMEZONE")
    schedule_summary_morning: str = Field(default="09:00", alias="SCHEDULE_SUMMARY_MORNING")
    schedule_summary_afternoon: str = Field(default="16:00", alias="SCHEDULE_SUMMARY_AFTERNOON")
    schedule_summary_night: str = Field(default="20:00", alias="SCHEDULE_SUMMARY_NIGHT")
    schedule_summary_evening: str | None = Field(default=None, alias="SCHEDULE_SUMMARY_EVENING")
    api_auth_key: str | None = Field(default=None, alias="API_AUTH_KEY")
    cors_origins: str = Field(
        default="http://localhost:5173", alias="CORS_ORIGINS"
    )

    default_categories: str = Field(
        default=_DEFAULT_CATEGORIES_ENV_VALUE,
        alias="DEFAULT_CATEGORIES",
    )
    summary_candidates_per_category: int = Field(
        default=5, alias="SUMMARY_CANDIDATES_PER_CATEGORY"
    )
    summary_candidates_extended_limit: int = Field(
        default=8, alias="SUMMARY_CANDIDATES_EXTENDED_LIMIT"
    )
    summary_candidates_extended_categories: str = Field(
        default="politica, economia", alias="SUMMARY_CANDIDATES_EXTENDED_CATEGORIES"
    )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def categories_list(self) -> list[str]:
        return [c.strip() for c in self.default_categories.split(",")]

    @property
    def scraper_sources_list(self) -> list[str]:
        return [s.strip() for s in self.scraper_sources.split(",")]

    @property
    def llm_providers_list(self) -> list[dict]:
        order = [o.strip() for o in self.llm_fallback_order.split(",")]
        key_map = {
            "groq": self.groq_api_key,
            "github": self.github_api_key,
            "nvidia": self.nvidia_api_key,
            "openai": self.openai_api_key,
            "gemini": self.gemini_api_key,
        }
        result: list[dict] = []
        for name in order:
            key = key_map.get(name)
            if key:
                result.append({"provider": name, "api_key": key})
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
