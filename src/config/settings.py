from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="DEBUG", alias="LOG_LEVEL")

    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    llm_model_summarize: str = Field(default="llama-3.3-70b-versatile", alias="LLM_MODEL_SUMMARIZE")
    llm_model_classify: str = Field(default="llama-3.1-8b-instant", alias="LLM_MODEL_CLASSIFY")
    llm_model_rewrite: str = Field(default="llama-3.1-70b-versatile", alias="LLM_MODEL_REWRITE")

    news_api_key: Optional[str] = Field(default=None, alias="NEWS_API_KEY")
    news_api_country: str = Field(default="bo", alias="NEWS_API_COUNTRY")
    news_api_language: str = Field(default="es", alias="NEWS_API_LANGUAGE")

    scraper_enabled: bool = Field(default=True, alias="SCRAPER_ENABLED")
    scraper_concurrency: int = Field(default=3, alias="SCRAPER_CONCURRENCY")
    scraper_timeout: int = Field(default=30, alias="SCRAPER_TIMEOUT")
    scraper_config_path: Optional[str] = Field(
        default="config/sources.yaml", alias="SCRAPER_CONFIG_PATH"
    )
    scraper_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        alias="SCRAPER_USER_AGENT",
    )
    scraper_sources: str = Field(
        default="radiofides,unitel,reduno,redbolivision", alias="SCRAPER_SOURCES"
    )

    twilio_account_sid: Optional[str] = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(default=None, alias="TWILIO_PHONE_NUMBER")
    twilio_webhook_url: Optional[str] = Field(default=None, alias="TWILIO_WEBHOOK_URL")

    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(default=None, alias="TELEGRAM_WEBHOOK_URL")

    database_url: str = Field(
        default="postgresql+asyncpg://user:pass@localhost:5432/news_summarizer",
        alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    schedule_timezone: str = Field(default="America/La_Paz", alias="SCHEDULE_TIMEZONE")
    schedule_summary_morning: str = Field(default="08:00", alias="SCHEDULE_SUMMARY_MORNING")
    schedule_summary_evening: str = Field(default="18:00", alias="SCHEDULE_SUMMARY_EVENING")

    default_categories: str = Field(
        default="economia,politica,deportes", alias="DEFAULT_CATEGORIES"
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
    def llm_api_key(self) -> Optional[str]:
        if self.llm_provider == "groq":
            return self.groq_api_key
        return self.openai_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
