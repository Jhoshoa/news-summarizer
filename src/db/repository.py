from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    exists,
    func,
    or_,
    select,
)
from sqlalchemy import update as sql_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.processors.story_fingerprint import (
    build_canonical_key,
    build_content_fingerprint,
    story_similarity,
)

Base = declarative_base()

DEFAULT_CATEGORIES = {
    "economia": "Economia",
    "politica": "Politica",
    "deportes": "Deportes",
    "tecnologia": "Tecnologia",
    "entretenimiento": "Entretenimiento",
    "general": "General",
}


class Subscriber(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True)
    phone = Column(String(50), nullable=True, unique=True, index=True)
    telegram_id = Column(String(50), nullable=True, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    channel = Column(String(20), nullable=False, default="whatsapp")
    categories = Column(JSON, nullable=False, default=list)
    frequency = Column(String(20), nullable=False, default="diario")
    preferred_time = Column(String(20), nullable=False, default="manana")
    timezone = Column(String(50), nullable=False, default="America/La_Paz")
    consent_accepted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    unsubscribed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Subscriber {self.phone or self.telegram_id or self.email} active={self.is_active}>"


class NewsCategory(Base):
    __tablename__ = "news_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class NewsSource(Base):
    __tablename__ = "news_sources"
    __table_args__ = (UniqueConstraint("name", name="uq_news_sources_name"),)

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    source_type = Column(String(20), nullable=False, default="scraper")
    base_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (UniqueConstraint("url_hash", name="uq_news_articles_url_hash"),)

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False, index=True)
    url_hash = Column(String(64), nullable=False, index=True)
    canonical_key = Column(String(500), nullable=True)
    content_fingerprint = Column(String(64), nullable=True, index=True)
    story_cluster_id = Column(String(64), nullable=True, index=True)
    duplicate_of_article_id = Column(Integer, ForeignKey("news_articles.id"), nullable=True, index=True)
    duplicate_reason = Column(String(50), nullable=True)
    similarity_score = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    author = Column(String(200), nullable=True)
    image_url = Column(String(1000), nullable=True)
    source_id = Column(Integer, ForeignKey("news_sources.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("news_categories.id"), nullable=False, index=True)
    country = Column(String(50), nullable=True)
    published_at = Column(DateTime, nullable=False, index=True)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    raw_payload = Column(JSON, nullable=False, default=dict)
    score = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="running")
    requested_categories = Column(JSON, nullable=False, default=list)
    scraper_count = Column(Integer, nullable=False, default=0)
    newsapi_count = Column(Integer, nullable=False, default=0)
    inserted_count = Column(Integer, nullable=False, default=0)
    updated_count = Column(Integer, nullable=False, default=0)
    raw_collected_count = Column(Integer, nullable=False, default=0)
    usable_count = Column(Integer, nullable=False, default=0)
    quality_dropped_count = Column(Integer, nullable=False, default=0)
    deduplicated_count = Column(Integer, nullable=False, default=0)
    duplicate_dropped_count = Column(Integer, nullable=False, default=0)
    ranked_count = Column(Integer, nullable=False, default=0)
    summary_candidates_count = Column(Integer, nullable=False, default=0)
    summaries_count = Column(Integer, nullable=False, default=0)
    used_cached_articles = Column(Boolean, nullable=False, default=False)
    used_cached_summaries = Column(Boolean, nullable=False, default=False)
    metrics_payload = Column(JSON, nullable=False, default=dict)
    error_message = Column(Text, nullable=True)


class NewsSummary(Base):
    __tablename__ = "news_summaries"
    __table_args__ = (
        UniqueConstraint("category_id", "summary_date", "title", name="uq_summary_day_title"),
    )

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("news_articles.id"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("news_categories.id"), nullable=False, index=True)
    story_cluster_id = Column(String(64), nullable=True, index=True)
    source_article_count = Column(Integer, nullable=False, default=1)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=False)
    fact = Column(Text, nullable=True)
    llm_provider = Column(String(50), nullable=True)
    llm_model = Column(String(100), nullable=True)
    summary_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Database:
    """Repositorio de base de datos."""

    IMPACT_MINUTES_PER_ARTICLE = 0.5
    IMPACT_MB_PER_PAGE = 0.8
    STORY_LOOKBACK_DAYS = 3
    STORY_SIMILARITY_THRESHOLD = 0.85
    IMPACT_METHODOLOGY_NOTE = (
        "Estimaciones orientativas basadas en articulos evitados."
    )

    def __init__(self, url: str, pool_size: int = 10, max_overflow: int = 20):
        self.engine = create_async_engine(
            url,
            echo=False,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
        )
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("Database inicializada")

    async def init_db(self):
        """Crea las tablas y semillas de referencia."""

        async with self.engine.begin() as conn:
            for table in Base.metadata.sorted_tables:
                try:
                    await conn.run_sync(table.create, checkfirst=True)
                except IntegrityError:
                    logger.warning(f"Tabla {table.name} ya existe, omitiendo")

        async with self.session_maker() as session:
            await self._seed_categories(session)
            await session.commit()

        logger.info("Base de datos inicializada")

    async def save_subscription(
        self,
        phone: str | None = None,
        telegram_id: str | None = None,
        email: str | None = None,
        channel: str = "whatsapp",
        categories: set[str] | None = None,
        frequency: str = "diario",
        preferred_time: str = "manana",
        timezone: str = "America/La_Paz",
        consent_accepted: bool = False,
    ) -> bool:
        """Guarda o actualiza una suscripcion."""

        if not phone and not telegram_id and not email:
            logger.error("Se requiere phone, telegram_id o email")
            return False

        async with self.session_maker() as session:
            subscriber = await self._find_subscriber(session, phone, telegram_id, email)

            if subscriber:
                if categories:
                    subscriber.categories = sorted(categories)
                subscriber.phone = phone
                subscriber.telegram_id = telegram_id
                subscriber.email = email
                subscriber.channel = channel
                subscriber.frequency = frequency
                subscriber.preferred_time = preferred_time
                subscriber.timezone = timezone
                subscriber.consent_accepted = consent_accepted
                subscriber.updated_at = datetime.utcnow()
                subscriber.is_active = True
                subscriber.unsubscribed_at = None
                logger.info(f"Actualizada suscripcion: {phone or telegram_id or email}")
            else:
                subscriber = Subscriber(
                    phone=phone,
                    telegram_id=telegram_id,
                    email=email,
                    channel=channel,
                    categories=sorted(categories) if categories else ["general"],
                    frequency=frequency,
                    preferred_time=preferred_time,
                    timezone=timezone,
                    consent_accepted=consent_accepted,
                )
                session.add(subscriber)
                logger.info(f"Nueva suscripcion: {phone or telegram_id or email}")

            await session.commit()
            return True

    async def get_active_subscribers(self) -> list[Subscriber]:
        """Obtiene todos los subscribers activos."""

        async with self.session_maker() as session:
            stmt = select(Subscriber).where(Subscriber.is_active.is_(True))
            result = await session.execute(stmt)
            subscribers = list(result.scalars().all())
            logger.info(f"Obtenidos {len(subscribers)} subscribers activos")
            return subscribers

    async def get_subscriber_by_phone(self, phone: str) -> Subscriber | None:
        """Obtiene un subscriber por telefono."""

        async with self.session_maker() as session:
            stmt = select(Subscriber).where(Subscriber.phone == phone)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_subscriber_by_telegram(
        self, telegram_id: str
    ) -> Subscriber | None:
        """Obtiene un subscriber por telegram ID."""

        async with self.session_maker() as session:
            stmt = select(Subscriber).where(Subscriber.telegram_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def unsubscribe(self, identifier: str) -> bool:
        """Desactiva una suscripcion."""

        async with self.session_maker() as session:
            stmt = (
                sql_update(Subscriber)
                .where(
                    (Subscriber.phone == identifier)
                    | (Subscriber.telegram_id == identifier)
                    | (Subscriber.email == identifier)
                )
                .values(
                    is_active=False,
                    updated_at=datetime.utcnow(),
                    unsubscribed_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Desactivada suscripcion: {identifier}")
            return True

    async def get_subscription_count(self) -> int:
        """Cuenta subscribers activos."""

        async with self.session_maker() as session:
            stmt = select(func.count()).select_from(Subscriber).where(
                Subscriber.is_active.is_(True)
            )
            result = await session.execute(stmt)
            return int(result.scalar_one())

    async def get_preference_preview(
        self,
        categories: list[str],
        *,
        limit: int = 5,
    ) -> list[dict]:
        """Obtiene summaries recientes para previsualizar un brief sin llamar al LLM."""

        normalized_categories = [category for category in categories if category in DEFAULT_CATEGORIES]
        if not normalized_categories:
            return []

        async with self.session_maker() as session:
            query_limit = max(int(limit), 1) * 3
            stmt = (
                select(NewsSummary, NewsCategory.name)
                .join(NewsCategory, NewsSummary.category_id == NewsCategory.id)
                .where(NewsCategory.name.in_(normalized_categories))
                .order_by(NewsSummary.summary_date.desc(), NewsSummary.created_at.desc())
                .limit(query_limit)
            )
            result = await session.execute(stmt)
            items = []
            seen_titles: set[str] = set()
            for summary, category_name in result.all():
                title_key = self._summary_title_key(summary.title)
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                slug = self._category_slug(category_name)
                items.append(
                    {
                        "category": slug,
                        "title": summary.title,
                        "summary": summary.summary,
                        "fact": summary.fact,
                        "summary_date": summary.summary_date,
                    }
                )
                if len(items) >= limit:
                    break
            return items

    async def start_collection_run(self, requested_categories: list[str]) -> int:
        async with self.session_maker() as session:
            run = CollectionRun(requested_categories=requested_categories)
            session.add(run)
            await session.flush()
            run_id = int(run.id)
            await session.commit()
            return run_id

    async def finish_collection_run(
        self,
        run_id: int,
        *,
        status: str,
        scraper_count: int = 0,
        newsapi_count: int = 0,
        inserted_count: int = 0,
        updated_count: int = 0,
        raw_collected_count: int = 0,
        usable_count: int = 0,
        quality_dropped_count: int = 0,
        deduplicated_count: int = 0,
        duplicate_dropped_count: int = 0,
        ranked_count: int = 0,
        summary_candidates_count: int = 0,
        summaries_count: int = 0,
        used_cached_articles: bool = False,
        used_cached_summaries: bool = False,
        metrics_payload: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        async with self.session_maker() as session:
            stmt = (
                sql_update(CollectionRun)
                .where(CollectionRun.id == run_id)
                .values(
                    finished_at=datetime.utcnow(),
                    status=status,
                    scraper_count=scraper_count,
                    newsapi_count=newsapi_count,
                    inserted_count=inserted_count,
                    updated_count=updated_count,
                    raw_collected_count=max(int(raw_collected_count), 0),
                    usable_count=max(int(usable_count), 0),
                    quality_dropped_count=max(int(quality_dropped_count), 0),
                    deduplicated_count=max(int(deduplicated_count), 0),
                    duplicate_dropped_count=max(int(duplicate_dropped_count), 0),
                    ranked_count=max(int(ranked_count), 0),
                    summary_candidates_count=max(int(summary_candidates_count), 0),
                    summaries_count=max(int(summaries_count), 0),
                    used_cached_articles=used_cached_articles,
                    used_cached_summaries=used_cached_summaries,
                    metrics_payload=metrics_payload or {},
                    error_message=error_message,
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def get_impact_metrics(
        self,
        metrics_date: date,
        *,
        fallback_to_latest: bool = True,
    ) -> dict[str, Any]:
        requested_date = metrics_date
        effective_date = metrics_date

        async with self.session_maker() as session:
            counts = await self._impact_counts_for_date(session, effective_date)
            if not counts["has_data"] and fallback_to_latest:
                latest_date = await self._latest_impact_date(session, requested_date)
                if latest_date and latest_date != requested_date:
                    effective_date = latest_date
                    counts = await self._impact_counts_for_date(session, effective_date)

        return self._build_impact_metrics_payload(
            effective_date=effective_date,
            requested_date=requested_date,
            is_fallback=effective_date != requested_date,
            collected_articles=counts["collected_articles"],
            unique_articles=counts["unique_articles"],
            summaries=counts["summaries"],
            cache_reused=counts["cache_reused"],
            has_data=counts["has_data"],
            data_source=counts["data_source"],
            quality_dropped_articles=counts["quality_dropped_articles"],
            duplicate_articles=counts["duplicate_articles"],
            summary_candidates=counts["summary_candidates"],
            usable_articles=counts["usable_articles"],
            ranked_articles=counts["ranked_articles"],
        )

    async def _impact_counts_for_date(
        self,
        session: AsyncSession,
        metrics_date: date,
    ) -> dict[str, Any]:
        article_start, article_end = self._day_bounds(metrics_date)

        unique_articles = int(
            await session.scalar(
                select(func.count(NewsArticle.id)).where(
                    NewsArticle.is_active.is_(True),
                    NewsArticle.published_at >= article_start,
                    NewsArticle.published_at < article_end,
                )
            )
            or 0
        )
        summaries = int(
            await session.scalar(
                select(func.count(NewsSummary.id)).where(NewsSummary.summary_date == metrics_date)
            )
            or 0
        )
        latest_run = await self._latest_collection_run_for_date(session, metrics_date)
        run_has_pipeline_metrics = self._collection_run_has_pipeline_metrics(latest_run)
        if latest_run and run_has_pipeline_metrics:
            collected_articles = max(
                self._safe_int(latest_run.raw_collected_count),
                self._safe_int(latest_run.scraper_count) + self._safe_int(latest_run.newsapi_count),
                unique_articles,
            )
            unique_from_run = self._safe_int(latest_run.deduplicated_count) or unique_articles
            summaries_from_run = self._impact_summary_count(
                stored_summaries=summaries,
                run_summaries=latest_run.summaries_count,
            )
            return {
                "data_source": "pipeline_run",
                "collected_articles": collected_articles,
                "unique_articles": unique_from_run,
                "summaries": summaries_from_run,
                "quality_dropped_articles": self._safe_int(latest_run.quality_dropped_count),
                "duplicate_articles": self._safe_int(latest_run.duplicate_dropped_count),
                "summary_candidates": self._safe_int(latest_run.summary_candidates_count),
                "usable_articles": self._safe_int(latest_run.usable_count),
                "ranked_articles": self._safe_int(latest_run.ranked_count),
                "cache_reused": bool(
                    latest_run.used_cached_articles or latest_run.used_cached_summaries
                ),
                "has_data": collected_articles > 0 or unique_from_run > 0 or summaries_from_run > 0,
            }

        collected_from_run = (
            self._safe_int(latest_run.scraper_count) + self._safe_int(latest_run.newsapi_count)
            if latest_run
            else 0
        )
        collected_articles = max(collected_from_run, unique_articles)

        return {
            "data_source": "derived" if collected_articles > 0 or summaries > 0 else "empty",
            "collected_articles": collected_articles,
            "unique_articles": unique_articles,
            "summaries": summaries,
            "quality_dropped_articles": 0,
            "duplicate_articles": max(collected_articles - unique_articles, 0),
            "summary_candidates": summaries,
            "usable_articles": unique_articles,
            "ranked_articles": unique_articles,
            "cache_reused": False,
            "has_data": collected_articles > 0 or unique_articles > 0 or summaries > 0,
        }

    def _collection_run_has_pipeline_metrics(self, run: CollectionRun | None) -> bool:
        if not run:
            return False
        return any(
            self._safe_int(getattr(run, field, 0)) > 0
            for field in (
                "raw_collected_count",
                "usable_count",
                "quality_dropped_count",
                "deduplicated_count",
                "duplicate_dropped_count",
                "ranked_count",
                "summary_candidates_count",
                "summaries_count",
            )
        ) or bool(getattr(run, "used_cached_articles", False)) or bool(
            getattr(run, "used_cached_summaries", False)
        )

    def _impact_summary_count(self, *, stored_summaries: int, run_summaries: Any) -> int:
        return max(self._safe_int(stored_summaries), self._safe_int(run_summaries))

    def _safe_int(self, value: Any) -> int:
        try:
            return max(int(value or 0), 0)
        except (TypeError, ValueError):
            return 0

    async def _latest_collection_run_for_date(
        self,
        session: AsyncSession,
        metrics_date: date,
    ) -> CollectionRun | None:
        start_at, end_at = self._day_bounds(metrics_date)
        stmt = (
            select(CollectionRun)
            .where(CollectionRun.started_at >= start_at, CollectionRun.started_at < end_at)
            .order_by(CollectionRun.started_at.desc(), CollectionRun.id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _latest_impact_date(
        self,
        session: AsyncSession,
        before_or_on: date,
    ) -> date | None:
        end_at = datetime.combine(before_or_on + timedelta(days=1), time.min)
        latest_article_date = await session.scalar(
            select(func.max(func.date(NewsArticle.published_at))).where(
                NewsArticle.is_active.is_(True),
                NewsArticle.published_at < end_at,
            )
        )
        latest_summary_date = await session.scalar(
            select(func.max(NewsSummary.summary_date)).where(
                NewsSummary.summary_date <= before_or_on,
            )
        )
        latest_run_date = await session.scalar(
            select(func.max(func.date(CollectionRun.started_at))).where(
                CollectionRun.started_at < end_at,
            )
        )

        candidates = [
            self._coerce_date_candidate(value)
            for value in (latest_article_date, latest_summary_date, latest_run_date)
        ]
        valid_candidates = [value for value in candidates if value is not None]
        return max(valid_candidates) if valid_candidates else None

    def _build_impact_metrics_payload(
        self,
        *,
        effective_date: date,
        requested_date: date,
        is_fallback: bool,
        collected_articles: int,
        unique_articles: int,
        summaries: int,
        cache_reused: bool = False,
        has_data: bool = True,
        data_source: str = "derived",
        quality_dropped_articles: int = 0,
        duplicate_articles: int | None = None,
        summary_candidates: int = 0,
        usable_articles: int = 0,
        ranked_articles: int = 0,
    ) -> dict[str, Any]:
        collected_articles = max(int(collected_articles), 0)
        unique_articles = max(int(unique_articles), 0)
        summaries = max(int(summaries), 0)
        duplicate_articles_estimated = max(
            int(duplicate_articles)
            if duplicate_articles is not None
            else collected_articles - unique_articles,
            0,
        )
        estimated_pages_avoided = max(collected_articles - summaries, 0)
        estimated_minutes_saved = round(
            estimated_pages_avoided * self.IMPACT_MINUTES_PER_ARTICLE,
            1,
        )
        estimated_data_saved_mb = round(estimated_pages_avoided * self.IMPACT_MB_PER_PAGE, 1)
        reduction_rate = (
            round(1 - (summaries / collected_articles), 4) if collected_articles > 0 else 0.0
        )

        return {
            "date": effective_date,
            "requested_date": requested_date,
            "is_fallback": is_fallback,
            "has_data": has_data,
            "data_source": data_source,
            "collected_articles": collected_articles,
            "unique_articles": unique_articles,
            "summaries": summaries,
            "quality_dropped_articles": max(int(quality_dropped_articles), 0),
            "duplicate_articles": duplicate_articles_estimated,
            "summary_candidates": max(int(summary_candidates), 0),
            "usable_articles": max(int(usable_articles), 0),
            "ranked_articles": max(int(ranked_articles), 0),
            "duplicate_articles_estimated": duplicate_articles_estimated,
            "reduction_rate": max(min(reduction_rate, 1.0), 0.0),
            "estimated_pages_avoided": estimated_pages_avoided,
            "estimated_minutes_saved": estimated_minutes_saved,
            "estimated_data_saved_mb": estimated_data_saved_mb,
            "cache_reused": cache_reused,
            "ai_calls_avoided_estimated": duplicate_articles_estimated,
            "pipeline": [
                {"label": "Recolectadas", "value": collected_articles},
                {"label": "Unicas", "value": unique_articles},
                {"label": "Briefs", "value": summaries},
            ],
            "methodology": {
                "minutes_per_article": self.IMPACT_MINUTES_PER_ARTICLE,
                "mb_per_page": self.IMPACT_MB_PER_PAGE,
                "note": self.IMPACT_METHODOLOGY_NOTE,
            },
        }

    def _coerce_date_candidate(self, value: Any) -> date | None:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
        return None

    async def upsert_articles(self, articles: list[dict]) -> dict[str, int]:
        inserted = 0
        updated = 0
        historical_duplicates = 0

        async with self.session_maker() as session:
            category_cache: dict[str, NewsCategory] = {}
            source_cache: dict[str, NewsSource] = {}

            for article in articles:
                url = article.get("url")
                title = article.get("title")
                if not url or not title:
                    continue

                url_hash = article.get("hash")
                if not url_hash:
                    continue

                category_name = str(article.get("category") or "general").strip().lower()
                source_name = str(article.get("source") or "unknown").strip()
                source_type = str(article.get("source_type") or "scraper")
                source_url = article.get("source_url")

                category = await self._get_or_create_category(
                    session, category_name, category_cache
                )
                source = await self._get_or_create_source(
                    session,
                    source_name,
                    source_type=source_type,
                    base_url=source_url,
                    cache=source_cache,
                )

                existing = await self._get_article_by_hash(session, url_hash)
                canonical_key = build_canonical_key(article)
                content_fingerprint = build_content_fingerprint(article)
                article["canonical_key"] = canonical_key
                article["content_fingerprint"] = content_fingerprint
                published_at = self._coerce_datetime(article.get("published_at"))
                score = self._coerce_score(article.get("score"))

                if existing:
                    article["id"] = existing.id
                    should_update_published_at = self._should_update_article_published_at(
                        article,
                        existing.published_at,
                    )
                    existing.title = title
                    existing.url = url
                    existing.description = article.get("description")
                    existing.content = article.get("content")
                    existing.author = article.get("author")
                    existing.image_url = article.get("image")
                    existing.source_id = source.id
                    existing.category_id = category.id
                    existing.canonical_key = canonical_key
                    existing.content_fingerprint = content_fingerprint
                    existing.story_cluster_id = existing.story_cluster_id or content_fingerprint
                    existing.country = article.get("country")
                    if should_update_published_at:
                        existing.published_at = published_at
                        existing.score = score
                    else:
                        article["published_at"] = existing.published_at
                        article["score"] = existing.score
                    existing.is_active = True
                    self._copy_story_metadata_to_payload(article, existing)
                    existing.raw_payload = self._normalize_payload(article)
                    updated += 1
                else:
                    story_match = await self.find_recent_story_match(
                        session,
                        article,
                        category_id=int(category.id),
                        published_at=published_at,
                    )
                    duplicate_of_article_id = None
                    duplicate_reason = None
                    similarity_score = None
                    story_cluster_id = content_fingerprint
                    if story_match:
                        matched_article, duplicate_reason, similarity_score = story_match
                        duplicate_of_article_id = matched_article.id
                        story_cluster_id = (
                            matched_article.story_cluster_id
                            or matched_article.content_fingerprint
                            or content_fingerprint
                        )
                        historical_duplicates += 1

                    article["story_cluster_id"] = story_cluster_id
                    article["duplicate_of_article_id"] = duplicate_of_article_id
                    article["duplicate_reason"] = duplicate_reason
                    article["similarity_score"] = similarity_score
                    payload = self._normalize_payload(article)

                    news_article = NewsArticle(
                        title=title,
                        url=url,
                        url_hash=url_hash,
                        canonical_key=canonical_key,
                        content_fingerprint=content_fingerprint,
                        story_cluster_id=story_cluster_id,
                        duplicate_of_article_id=duplicate_of_article_id,
                        duplicate_reason=duplicate_reason,
                        similarity_score=similarity_score,
                        description=article.get("description"),
                        content=article.get("content"),
                        author=article.get("author"),
                        image_url=article.get("image"),
                        source_id=source.id,
                        category_id=category.id,
                        country=article.get("country"),
                        published_at=published_at,
                        collected_at=datetime.utcnow(),
                        raw_payload=payload,
                        score=score,
                        is_active=True,
                    )
                    session.add(news_article)
                    await session.flush()
                    article["id"] = news_article.id
                    inserted += 1

            await session.commit()

        return {
            "inserted": inserted,
            "updated": updated,
            "historical_duplicates": historical_duplicates,
        }

    async def find_recent_story_match(
        self,
        session: AsyncSession,
        article: dict,
        *,
        category_id: int,
        published_at: datetime,
        lookback_days: int | None = None,
    ) -> tuple[NewsArticle, str, float] | None:
        lookback = max(int(lookback_days or self.STORY_LOOKBACK_DAYS), 1)
        cutoff = published_at - timedelta(days=lookback)
        fingerprint = article.get("content_fingerprint") or build_content_fingerprint(article)

        exact_stmt = (
            select(NewsArticle)
            .where(
                NewsArticle.is_active.is_(True),
                NewsArticle.category_id == category_id,
                NewsArticle.published_at >= cutoff,
                NewsArticle.content_fingerprint == fingerprint,
            )
            .order_by(
                NewsArticle.duplicate_of_article_id.isnot(None),
                NewsArticle.published_at.desc(),
                NewsArticle.id.asc(),
            )
            .limit(1)
        )
        exact_result = await session.execute(exact_stmt)
        exact_match = exact_result.scalar_one_or_none()
        if exact_match:
            return exact_match, "fingerprint", 1.0

        candidates_stmt = (
            select(NewsArticle)
            .where(
                NewsArticle.is_active.is_(True),
                NewsArticle.category_id == category_id,
                NewsArticle.published_at >= cutoff,
            )
            .order_by(NewsArticle.published_at.desc(), NewsArticle.collected_at.desc())
            .limit(100)
        )
        candidates_result = await session.execute(candidates_stmt)

        best_match: NewsArticle | None = None
        best_score = 0.0
        for candidate in candidates_result.scalars().all():
            score = story_similarity(
                article,
                self._article_for_story_matching(candidate, article.get("category")),
            )
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_match and best_score >= self.STORY_SIMILARITY_THRESHOLD:
            reason = "title_similarity" if best_score < 0.96 else "content_similarity"
            return best_match, reason, best_score

        return None

    async def get_recent_articles(
        self,
        categories: list[str],
        since: datetime,
        limit: int | None = None,
    ) -> list[dict]:
        async with self.session_maker() as session:
            stmt = (
                select(NewsArticle, NewsCategory.name, NewsSource.name, NewsSource.source_type)
                .join(NewsCategory, NewsArticle.category_id == NewsCategory.id)
                .join(NewsSource, NewsArticle.source_id == NewsSource.id)
                .where(
                    NewsArticle.is_active.is_(True),
                    NewsArticle.published_at >= since,
                    NewsCategory.name.in_(categories),
                )
                .order_by(NewsArticle.published_at.desc(), NewsArticle.collected_at.desc())
            )
            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            rows = result.all()

        return [self._article_row_to_dict(row) for row in rows]

    async def list_articles(
        self,
        *,
        category: str | None = None,
        source: str | None = None,
        q: str | None = None,
        article_date: date | None = None,
        fallback_to_latest: bool = False,
        exclude_summarized: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size
        requested_date = article_date
        effective_date = article_date
        is_fallback = False

        async with self.session_maker() as session:
            filters = self._article_filters(
                category=category,
                source=source,
                q=q,
                article_date=effective_date,
                exclude_summarized=exclude_summarized,
            )
            total_stmt = (
                select(func.count(NewsArticle.id))
                .join(NewsCategory, NewsArticle.category_id == NewsCategory.id)
                .join(NewsSource, NewsArticle.source_id == NewsSource.id)
                .where(*filters)
            )
            total = int(await session.scalar(total_stmt) or 0)

            if total == 0 and fallback_to_latest and requested_date:
                latest_date = await self._latest_article_date(
                    session,
                    category=category,
                    source=source,
                    q=q,
                    before_or_on=requested_date,
                    exclude_summarized=exclude_summarized,
                )
                if latest_date and latest_date != requested_date:
                    effective_date = latest_date
                    is_fallback = True
                    filters = self._article_filters(
                        category=category,
                        source=source,
                        q=q,
                        article_date=effective_date,
                        exclude_summarized=exclude_summarized,
                    )
                    total_stmt = (
                        select(func.count(NewsArticle.id))
                        .join(NewsCategory, NewsArticle.category_id == NewsCategory.id)
                        .join(NewsSource, NewsArticle.source_id == NewsSource.id)
                        .where(*filters)
                    )
                    total = int(await session.scalar(total_stmt) or 0)

            stmt = (
                select(NewsArticle, NewsCategory.name, NewsSource.name, NewsSource.source_type)
                .join(NewsCategory, NewsArticle.category_id == NewsCategory.id)
                .join(NewsSource, NewsArticle.source_id == NewsSource.id)
                .where(*filters)
                .order_by(NewsArticle.published_at.desc(), NewsArticle.collected_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            rows = result.all()

        return self._paginated_response(
            items=[self._article_row_to_dict(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
            date=effective_date,
            requested_date=requested_date,
            is_fallback=is_fallback,
        )

    def _article_filters(
        self,
        *,
        category: str | None = None,
        source: str | None = None,
        q: str | None = None,
        article_date: date | None = None,
        exclude_summarized: bool = False,
    ) -> list[Any]:
        filters = [NewsArticle.is_active.is_(True)]
        if article_date:
            start_at, end_at = self._day_bounds(article_date)
            filters.extend(
                [
                    NewsArticle.published_at >= start_at,
                    NewsArticle.published_at < end_at,
                ]
            )
        if exclude_summarized:
            filters.append(self._article_not_summarized_filter(article_date))
        if category:
            filters.append(NewsCategory.name == category.strip().lower())
        if source:
            filters.append(func.lower(NewsSource.name) == source.strip().lower())
        if q:
            term = f"%{q.strip()}%"
            filters.append(
                or_(
                    NewsArticle.title.ilike(term),
                    NewsArticle.description.ilike(term),
                    NewsArticle.content.ilike(term),
                )
            )
        return filters

    def _article_not_summarized_filter(self, article_date: date | None = None) -> Any:
        summarized_article_exists = exists().where(
            NewsSummary.article_id == NewsArticle.id,
        )
        return ~summarized_article_exists

    async def _latest_article_date(
        self,
        session: AsyncSession,
        *,
        category: str | None = None,
        source: str | None = None,
        q: str | None = None,
        before_or_on: date,
        exclude_summarized: bool = False,
    ) -> date | None:
        filters = self._article_filters(category=category, source=source, q=q)
        end_at = datetime.combine(before_or_on + timedelta(days=1), time.min)
        filters.append(NewsArticle.published_at < end_at)
        if exclude_summarized:
            filters.append(self._article_not_summarized_filter())

        stmt = (
            select(func.max(func.date(NewsArticle.published_at)))
            .join(NewsCategory, NewsArticle.category_id == NewsCategory.id)
            .join(NewsSource, NewsArticle.source_id == NewsSource.id)
            .where(*filters)
        )
        return await session.scalar(stmt)

    def _day_bounds(self, value: date) -> tuple[datetime, datetime]:
        start_at = datetime.combine(value, time.min)
        return start_at, start_at + timedelta(days=1)

    async def get_article_by_id(self, article_id: int) -> dict | None:
        async with self.session_maker() as session:
            stmt = (
                select(NewsArticle, NewsCategory.name, NewsSource.name, NewsSource.source_type)
                .join(NewsCategory, NewsArticle.category_id == NewsCategory.id)
                .join(NewsSource, NewsArticle.source_id == NewsSource.id)
                .where(NewsArticle.id == article_id, NewsArticle.is_active.is_(True))
            )
            result = await session.execute(stmt)
            row = result.first()

        return self._article_row_to_dict(row) if row else None

    async def get_related_articles(self, article_id: int) -> dict | None:
        async with self.session_maker() as session:
            article = await session.get(NewsArticle, article_id)
            if not article or not article.is_active:
                return None

            cluster_id = article.story_cluster_id
            canonical_article_id = article.duplicate_of_article_id or article.id
            if not cluster_id:
                return {
                    "story_cluster_id": None,
                    "canonical_article_id": canonical_article_id,
                    "items": [],
                }

            stmt = (
                select(NewsArticle, NewsCategory.name, NewsSource.name, NewsSource.source_type)
                .join(NewsCategory, NewsArticle.category_id == NewsCategory.id)
                .join(NewsSource, NewsArticle.source_id == NewsSource.id)
                .where(
                    NewsArticle.is_active.is_(True),
                    NewsArticle.story_cluster_id == cluster_id,
                )
                .order_by(
                    NewsArticle.duplicate_of_article_id.isnot(None),
                    NewsArticle.published_at.asc(),
                    NewsArticle.id.asc(),
                )
            )
            result = await session.execute(stmt)
            rows = result.all()

        items = [self._article_row_to_dict(row) for row in rows]
        for item in items:
            if item["duplicate_of_article_id"] is None:
                canonical_article_id = item["id"]
                break

        return {
            "story_cluster_id": cluster_id,
            "canonical_article_id": canonical_article_id,
            "items": items,
        }

    async def save_summaries(
        self,
        summaries: list[dict],
        *,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        summary_date: date | None = None,
    ) -> dict[str, int]:
        inserted = 0
        updated = 0
        summary_date = summary_date or date.today()

        async with self.session_maker() as session:
            category_cache: dict[str, NewsCategory] = {}
            seen_story_keys: set[str] = set()

            for summary in summaries:
                title = str(summary.get("title") or "").strip()
                body = str(summary.get("summary") or "").strip()
                category_name = str(summary.get("category") or "general").strip().lower()
                if not title or not body:
                    continue

                story_key = f"{category_name}:{self._summary_story_key(summary)}"
                if story_key in seen_story_keys:
                    continue
                seen_story_keys.add(story_key)

                category = await self._get_or_create_category(
                    session, category_name, category_cache
                )
                article_id = summary.get("article_id")
                fact = summary.get("fact")
                story_cluster_id = summary.get("story_cluster_id")
                source_article_count = self._safe_int(summary.get("source_article_count")) or 1

                existing = await self._get_summary(session, category.id, summary_date, title)
                if existing:
                    existing.summary = body
                    existing.fact = fact
                    existing.llm_provider = llm_provider
                    existing.llm_model = llm_model
                    existing.article_id = article_id
                    existing.story_cluster_id = story_cluster_id
                    existing.source_article_count = source_article_count
                    updated += 1
                else:
                    session.add(
                        NewsSummary(
                            article_id=article_id,
                            category_id=category.id,
                            story_cluster_id=story_cluster_id,
                            source_article_count=source_article_count,
                            title=title,
                            summary=body,
                            fact=fact,
                            llm_provider=llm_provider,
                            llm_model=llm_model,
                            summary_date=summary_date,
                        )
                    )
                    inserted += 1

            await session.commit()

        return {"inserted": inserted, "updated": updated}

    async def get_recent_summaries(
        self,
        categories: list[str],
        summary_date: date | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        summary_date = summary_date or date.today()

        async with self.session_maker() as session:
            stmt = (
                select(
                    NewsSummary,
                    NewsCategory.name,
                    NewsArticle.url,
                    NewsArticle.title,
                    NewsSource.name,
                    NewsArticle.published_at,
                    NewsArticle.image_url,
                    NewsArticle.description,
                )
                .join(NewsCategory, NewsSummary.category_id == NewsCategory.id)
                .outerjoin(NewsArticle, NewsSummary.article_id == NewsArticle.id)
                .outerjoin(NewsSource, NewsArticle.source_id == NewsSource.id)
                .where(
                    NewsCategory.name.in_(categories),
                    NewsSummary.summary_date == summary_date,
                    NewsArticle.published_at.is_not(None),
                    func.date(NewsArticle.published_at) == summary_date,
                )
                .order_by(NewsSummary.created_at.desc())
            )
            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            rows = result.all()

        return [self._summary_row_to_dict(row) for row in rows]

    async def list_summaries(
        self,
        *,
        category: str | None = None,
        summary_date: date | None = None,
        article_id: int | None = None,
        fallback_to_latest: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size
        requested_date = summary_date or date.today()
        effective_date = requested_date
        is_fallback = False

        async with self.session_maker() as session:
            filters = self._summary_filters(
                category=category,
                summary_date=effective_date,
                article_id=article_id,
            )
            total_stmt = (
                select(func.count(NewsSummary.id))
                .join(NewsCategory, NewsSummary.category_id == NewsCategory.id)
                .outerjoin(NewsArticle, NewsSummary.article_id == NewsArticle.id)
                .outerjoin(NewsSource, NewsArticle.source_id == NewsSource.id)
                .where(*filters)
            )
            total = int(await session.scalar(total_stmt) or 0)

            if total == 0 and fallback_to_latest:
                latest_date = await self._latest_summary_date(
                    session,
                    category=category,
                    article_id=article_id,
                    before_or_on=requested_date,
                )
                if latest_date and latest_date != requested_date:
                    effective_date = latest_date
                    is_fallback = True
                    filters = self._summary_filters(
                        category=category,
                        summary_date=effective_date,
                        article_id=article_id,
                    )
                    total_stmt = (
                        select(func.count(NewsSummary.id))
                        .join(NewsCategory, NewsSummary.category_id == NewsCategory.id)
                        .outerjoin(NewsArticle, NewsSummary.article_id == NewsArticle.id)
                        .outerjoin(NewsSource, NewsArticle.source_id == NewsSource.id)
                        .where(*filters)
                    )
                    total = int(await session.scalar(total_stmt) or 0)

            stmt = (
                select(
                    NewsSummary,
                    NewsCategory.name,
                    NewsArticle.url,
                    NewsArticle.title,
                    NewsSource.name,
                    NewsArticle.published_at,
                    NewsArticle.image_url,
                    NewsArticle.description,
                )
                .join(NewsCategory, NewsSummary.category_id == NewsCategory.id)
                .outerjoin(NewsArticle, NewsSummary.article_id == NewsArticle.id)
                .outerjoin(NewsSource, NewsArticle.source_id == NewsSource.id)
                .where(*filters)
                .order_by(NewsArticle.published_at.desc(), NewsSummary.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            rows = result.all()

        return self._paginated_response(
            items=[self._summary_row_to_dict(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
            date=effective_date,
            requested_date=requested_date,
            is_fallback=is_fallback,
        )

    def _summary_filters(
        self,
        *,
        category: str | None = None,
        summary_date: date,
        article_id: int | None = None,
    ) -> list[Any]:
        filters = [
            NewsSummary.summary_date == summary_date,
        ]
        if category:
            filters.append(NewsCategory.name == category.strip().lower())
        if article_id is not None:
            filters.append(NewsSummary.article_id == article_id)
        return filters

    async def _latest_summary_date(
        self,
        session: AsyncSession,
        *,
        category: str | None = None,
        article_id: int | None = None,
        before_or_on: date,
    ) -> date | None:
        filters = [NewsSummary.summary_date <= before_or_on]
        if category:
            filters.append(NewsCategory.name == category.strip().lower())
        if article_id is not None:
            filters.append(NewsSummary.article_id == article_id)

        stmt = (
            select(func.max(NewsSummary.summary_date))
            .join(NewsCategory, NewsSummary.category_id == NewsCategory.id)
            .outerjoin(NewsArticle, NewsSummary.article_id == NewsArticle.id)
            .outerjoin(NewsSource, NewsArticle.source_id == NewsSource.id)
            .where(*filters)
        )
        return await session.scalar(stmt)

    async def get_summary_by_id(self, summary_id: int) -> dict | None:
        async with self.session_maker() as session:
            stmt = (
                select(
                    NewsSummary,
                    NewsCategory.name,
                    NewsArticle.url,
                    NewsArticle.title,
                    NewsSource.name,
                    NewsArticle.published_at,
                    NewsArticle.image_url,
                    NewsArticle.description,
                )
                .join(NewsCategory, NewsSummary.category_id == NewsCategory.id)
                .outerjoin(NewsArticle, NewsSummary.article_id == NewsArticle.id)
                .outerjoin(NewsSource, NewsArticle.source_id == NewsSource.id)
                .where(NewsSummary.id == summary_id)
            )
            result = await session.execute(stmt)
            row = result.first()

        return self._summary_row_to_dict(row) if row else None

    async def close(self):
        """Cierra el pool de conexiones."""
        await self.engine.dispose()
        logger.info("Database cerrada")

    async def _seed_categories(self, session: AsyncSession) -> None:
        for name, display_name in DEFAULT_CATEGORIES.items():
            existing = await self._get_category(session, name)
            if existing:
                existing.display_name = display_name
                existing.is_active = True
            else:
                session.add(
                    NewsCategory(
                        name=name,
                        display_name=display_name,
                        is_active=True,
                    )
                )

    async def _get_category(self, session: AsyncSession, name: str) -> NewsCategory | None:
        stmt = select(NewsCategory).where(NewsCategory.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_or_create_category(
        self,
        session: AsyncSession,
        name: str,
        cache: dict[str, NewsCategory],
    ) -> NewsCategory:
        if name in cache:
            return cache[name]

        category = await self._get_category(session, name)
        if not category:
            category = NewsCategory(
                name=name,
                display_name=DEFAULT_CATEGORIES.get(name, name.title()),
                is_active=True,
            )
            session.add(category)
            await session.flush()

        cache[name] = category
        return category

    async def _get_or_create_source(
        self,
        session: AsyncSession,
        name: str,
        *,
        source_type: str,
        base_url: str | None,
        cache: dict[str, NewsSource],
    ) -> NewsSource:
        key = f"{name}:{source_type}:{base_url or ''}"
        if key in cache:
            return cache[key]

        stmt = select(NewsSource).where(NewsSource.name == name)
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()
        if source:
            source.source_type = source_type
            source.base_url = base_url or source.base_url
            source.is_active = True
            source.updated_at = datetime.utcnow()
        else:
            source = NewsSource(
                name=name,
                source_type=source_type,
                base_url=base_url,
                is_active=True,
            )
            session.add(source)
            await session.flush()

        cache[key] = source
        return source

    async def _get_article_by_hash(
        self, session: AsyncSession, url_hash: str
    ) -> NewsArticle | None:
        stmt = select(NewsArticle).where(NewsArticle.url_hash == url_hash)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    def _article_for_story_matching(self, article: NewsArticle, category: str | None = None) -> dict:
        return {
            "title": article.title,
            "description": article.description,
            "content": article.content,
            "category": category or "",
            "canonical_key": article.canonical_key,
            "content_fingerprint": article.content_fingerprint,
        }

    def _copy_story_metadata_to_payload(self, target: dict, article: NewsArticle) -> None:
        target["canonical_key"] = article.canonical_key
        target["content_fingerprint"] = article.content_fingerprint
        target["story_cluster_id"] = article.story_cluster_id
        target["duplicate_of_article_id"] = article.duplicate_of_article_id
        target["duplicate_reason"] = article.duplicate_reason
        target["similarity_score"] = article.similarity_score

    async def _get_summary(
        self,
        session: AsyncSession,
        category_id: int,
        summary_date: date,
        title: str,
    ) -> NewsSummary | None:
        stmt = select(NewsSummary).where(
            NewsSummary.category_id == category_id,
            NewsSummary.summary_date == summary_date,
            NewsSummary.title == title,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    def _normalize_payload(self, article: dict) -> dict[str, Any]:
        return {key: self._json_safe_value(value) for key, value in article.items()}

    def _json_safe_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: self._json_safe_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe_value(item) for item in value]
        return value

    def _coerce_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value.replace(tzinfo=None) if value.tzinfo else value
        return datetime.now()

    def _should_update_article_published_at(
        self,
        article: dict[str, Any],
        existing_published_at: datetime | None,
    ) -> bool:
        if existing_published_at is None:
            return True
        return bool(
            article.get("published_at_from_detail")
            or article.get("published_at_from_listing")
            or article.get("source_type") != "scraper"
        )

    def _coerce_score(self, value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _article_row_to_dict(self, row: Any) -> dict:
        article, category_name, source_name, source_type = row
        return {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "description": article.description,
            "content": self._article_content_for_response(article.content, article.description),
            "author": article.author,
            "image": self._public_image_url(article.image_url),
            "published_at": article.published_at,
            "collected_at": article.collected_at,
            "source": source_name,
            "source_type": source_type,
            "category": category_name,
            "country": article.country,
            "hash": article.url_hash,
            "score": article.score,
            "canonical_key": getattr(article, "canonical_key", None),
            "content_fingerprint": getattr(article, "content_fingerprint", None),
            "story_cluster_id": getattr(article, "story_cluster_id", None),
            "duplicate_of_article_id": getattr(article, "duplicate_of_article_id", None),
            "duplicate_reason": getattr(article, "duplicate_reason", None),
            "similarity_score": getattr(article, "similarity_score", None),
            "raw_payload": article.raw_payload,
        }

    def _article_content_for_response(
        self,
        content: str | None,
        description: str | None,
    ) -> str | None:
        if not content:
            return None

        normalized_content = self._normalize_article_text(content)
        normalized_description = self._normalize_article_text(description)
        if normalized_description and normalized_content == normalized_description:
            return None

        return content

    def _normalize_article_text(self, value: str | None) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip().lower()

    def _category_slug(self, display_name: str | None) -> str:
        reverse_categories = {display_name: slug for slug, display_name in DEFAULT_CATEGORIES.items()}
        return reverse_categories.get(str(display_name or ""), str(display_name or "general").lower())

    def _summary_title_key(self, title: str | None) -> str:
        normalized = self._normalize_article_text(title)
        normalized = re.sub(r"[^\w\s]", "", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _summary_story_key(self, summary: dict) -> str:
        story_cluster_id = str(summary.get("story_cluster_id") or "").strip()
        if story_cluster_id:
            return f"cluster:{story_cluster_id}"
        return f"title:{self._summary_title_key(summary.get('title'))}"

    def _summary_row_to_dict(self, row: Any) -> dict:
        summary = row[0]
        category_name = row[1]
        article_url = row[2] if len(row) > 2 else None
        article_title = row[3] if len(row) > 3 else None
        source_name = row[4] if len(row) > 4 else None
        published_at = row[5] if len(row) > 5 else None
        image_url = self._public_image_url(row[6] if len(row) > 6 else None)
        article_description = row[7] if len(row) > 7 else None
        return {
            "id": summary.id,
            "article_id": summary.article_id,
            "story_cluster_id": getattr(summary, "story_cluster_id", None),
            "source_article_count": getattr(summary, "source_article_count", 1),
            "category": category_name,
            "title": summary.title,
            "summary": summary.summary,
            "fact": summary.fact,
            "source": source_name,
            "url": article_url,
            "article_title": article_title,
            "published_at": published_at,
            "image": image_url,
            "article_description": article_description,
            "llm_provider": summary.llm_provider,
            "llm_model": summary.llm_model,
            "summary_date": summary.summary_date,
            "created_at": summary.created_at,
        }

    def _public_image_url(self, value: str | None) -> str | None:
        if not value:
            return None

        image_url = value.strip()
        normalized = image_url.lower()
        blocked_hosts = ("tracker.metricool.com",)
        blocked_patterns = ("/c3po.jpg", "pixel", "tracker", "analytics")

        if any(host in normalized for host in blocked_hosts):
            return None
        if any(pattern in normalized for pattern in blocked_patterns):
            return None

        return image_url

    def _paginated_response(
        self,
        *,
        items: list[dict],
        total: int,
        page: int,
        page_size: int,
        date: date | None = None,
        requested_date: date | None = None,
        is_fallback: bool = False,
    ) -> dict[str, Any]:
        total_pages = (total + page_size - 1) // page_size if total else 0
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "date": date,
            "requested_date": requested_date,
            "is_fallback": is_fallback,
        }

    async def _find_subscriber(
        self,
        session: AsyncSession,
        phone: str | None,
        telegram_id: str | None,
        email: str | None,
    ) -> Subscriber | None:
        filters = []
        if phone:
            filters.append(Subscriber.phone == phone)
        if telegram_id:
            filters.append(Subscriber.telegram_id == telegram_id)
        if email:
            filters.append(Subscriber.email == email)

        if not filters:
            return None

        stmt = select(Subscriber).where(or_(*filters))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
