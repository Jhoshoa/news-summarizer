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
    # Timeout por llamada a un proveedor LLM, en segundos. El SDK de OpenAI
    # por defecto usa 600s + 2 reintentos propios, lo que puede dejar un
    # proveedor lento/caido (nvidia, ver comentario arriba) colgado 20+
    # minutos antes de pasarle el turno al siguiente del LLMRouter.
    llm_timeout: float = Field(default=45.0, alias="LLM_TIMEOUT")
    # Cuantas categorias se resumen a la vez en _build_summaries (antes se
    # resumia una categoria a la vez, cada una un round-trip completo al
    # LLM). El LLMRouter ya reparte la carga con failover propio entre sus
    # providers, asi que esto solo acota cuantos de esos round-trips estan
    # en vuelo a la vez.
    summary_concurrency: int = Field(default=4, alias="SUMMARY_CONCURRENCY")

    scraper_enabled: bool = Field(default=True, alias="SCRAPER_ENABLED")
    # Cuantas fuentes se scrapean a la vez (antes esta variable existia pero
    # no se conectaba a nada -- el scraping corria una fuente a la vez).
    scraper_concurrency: int = Field(default=3, alias="SCRAPER_CONCURRENCY")
    # Cuantas paginas de detalle de UNA MISMA fuente se piden a la vez.
    # Limite aparte y mas chico a proposito: no queremos mandarle a un solo
    # sitio decenas de requests simultaneos aunque varias fuentes corran
    # juntas -- eso se veria como trafico abusivo del lado de esa fuente.
    scraper_detail_concurrency: int = Field(default=5, alias="SCRAPER_DETAIL_CONCURRENCY")
    scraper_timeout: int = Field(default=30, alias="SCRAPER_TIMEOUT")
    scraper_config_path: str | None = Field(
        default="config/sources.yaml", alias="SCRAPER_CONFIG_PATH"
    )
    scraper_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        alias="SCRAPER_USER_AGENT",
    )
    # Un articulo ya scrapeado (con contenido guardado) no se vuelve a pedir
    # completo si ya paso este numero de horas desde su publicacion -- antes
    # de eso se sigue re-chequeando por si la nota se actualiza (comun en
    # coberturas "en desarrollo").
    scraper_detail_refresh_hours: int = Field(
        default=3, alias="SCRAPER_DETAIL_REFRESH_HOURS"
    )

    # WhatsApp via la API directa de Meta (WhatsApp Cloud API), sin Twilio
    # ni otro intermediario -- Twilio exigia auto-recharge obligatorio o
    # suspendia la cuenta, ademas de cobrar su propio markup encima de la
    # tarifa de Meta.
    whatsapp_meta_access_token: str | None = Field(default=None, alias="WHATSAPP_META_ACCESS_TOKEN")
    whatsapp_meta_phone_number_id: str | None = Field(default=None, alias="WHATSAPP_META_PHONE_NUMBER_ID")
    whatsapp_meta_api_version: str = Field(default="v21.0", alias="WHATSAPP_META_API_VERSION")
    # Verifica la suscripcion del webhook (handshake GET de Meta).
    whatsapp_meta_verify_token: str | None = Field(default=None, alias="WHATSAPP_META_VERIFY_TOKEN")
    # Firma los eventos entrantes del webhook (X-Hub-Signature-256).
    whatsapp_meta_app_secret: str | None = Field(default=None, alias="WHATSAPP_META_APP_SECRET")

    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: str | None = Field(default=None, alias="TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: str | None = Field(default=None, alias="TELEGRAM_WEBHOOK_SECRET")

    email_enabled: bool = Field(default=False, alias="EMAIL_ENABLED")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="EcoBrief Bolivia", alias="SMTP_FROM_NAME")

    # Cuantos subscriptores se entregan a la vez en /trigger/delivery (antes
    # se enviaba uno por uno). Un solo limite para los 3 canales -- a
    # diferencia del scraper, cada subscriptor le pega a un solo proveedor
    # (Meta, Telegram o SMTP) segun su canal, no a la misma fuente repetida.
    delivery_concurrency: int = Field(default=5, alias="DELIVERY_CONCURRENCY")

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
