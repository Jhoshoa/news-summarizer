from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

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
    Time,
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

TZ_BOLIVIA = ZoneInfo("America/La_Paz")


def _now_bolivia() -> datetime:
    return datetime.now(TZ_BOLIVIA).replace(tzinfo=None)


Base = declarative_base()

DEFAULT_CATEGORIES = {
    "economia": "Economia",
    "politica": "Politica",
    "deportes": "Deportes",
    "tecnologia": "Tecnologia",
    "entretenimiento": "Entretenimiento",
    "policiales": "Policiales",
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
    created_at = Column(DateTime, nullable=False, default=_now_bolivia)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now_bolivia,
        onupdate=_now_bolivia,
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
    created_at = Column(DateTime, nullable=False, default=_now_bolivia)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now_bolivia,
        onupdate=_now_bolivia,
    )


class NewsSource(Base):
    __tablename__ = "news_sources"
    __table_args__ = (UniqueConstraint("name", name="uq_news_sources_name"),)

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    source_type = Column(String(20), nullable=False, default="scraper")
    base_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=_now_bolivia)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now_bolivia,
        onupdate=_now_bolivia,
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
    collected_at = Column(DateTime, nullable=False, default=_now_bolivia, index=True)
    raw_payload = Column(JSON, nullable=False, default=dict)
    score = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=_now_bolivia)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now_bolivia,
        onupdate=_now_bolivia,
    )


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, nullable=False, default=_now_bolivia)
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
    ai_dedup_count = Column(Integer, nullable=False, default=0)
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
    created_at = Column(DateTime, nullable=False, default=_now_bolivia)


class WorldCupMatch(Base):
    __tablename__ = "worldcup_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_date = Column(Date, nullable=False, index=True)
    match_time = Column(Time, nullable=False)
    group_name = Column(String(2), nullable=False)
    home_team = Column(String(50), nullable=False)
    away_team = Column(String(50), nullable=False)
    home_flag = Column(String(20), nullable=True)
    away_flag = Column(String(20), nullable=True)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    is_playing = Column(Boolean, default=False)
    is_finished = Column(Boolean, default=False)
    stage = Column(String(20), nullable=False, default="group")
    venue = Column(String(100), nullable=True)


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
            await self._seed_worldcup_matches(session)
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
                subscriber.updated_at = _now_bolivia()
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
                    updated_at=_now_bolivia(),
                    unsubscribed_at=_now_bolivia(),
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
        ai_dedup_count: int = 0,
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
                    finished_at=_now_bolivia(),
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
                    ai_dedup_count=max(int(ai_dedup_count), 0),
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

            runs_data = await self._build_runs_payload(session, effective_date)

        payload = self._build_impact_metrics_payload(
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
            inserted_articles=counts.get("inserted_articles", 0),
            updated_articles=counts.get("updated_articles", 0),
            duplicate_dropped_articles=counts.get("duplicate_dropped_articles", 0),
        )
        payload["runs"] = runs_data
        return payload

    async def _impact_counts_for_date(
        self,
        session: AsyncSession,
        metrics_date: date,
    ) -> dict[str, Any]:
        article_start, article_end = self._day_bounds(metrics_date)

        collected_articles = int(
            await session.scalar(
                select(func.count(NewsArticle.id)).where(
                    NewsArticle.published_at >= article_start,
                    NewsArticle.published_at < article_end,
                )
            )
            or 0
        )
        unique_articles = int(
            await session.scalar(
                select(func.count(NewsArticle.id)).where(
                    NewsArticle.published_at >= article_start,
                    NewsArticle.published_at < article_end,
                    NewsArticle.duplicate_of_article_id.is_(None),
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
        runs = await self._collection_runs_for_date(session, metrics_date)
        runs_with_metrics = [r for r in runs if self._collection_run_has_pipeline_metrics(r)]
        latest_run = runs_with_metrics[-1] if runs_with_metrics else None

        duplicate_articles = max(collected_articles - unique_articles, 0)
        derived = {
            "collected_articles": collected_articles,
            "unique_articles": unique_articles,
            "summaries": summaries,
            "quality_dropped_articles": 0,
            "duplicate_articles": duplicate_articles,
            "summary_candidates": unique_articles,
            "usable_articles": collected_articles,
            "ranked_articles": unique_articles,
            "has_data": collected_articles > 0 or unique_articles > 0 or summaries > 0,
        }

        if latest_run:
            cumulative_collected = sum(
                self._safe_int(r.raw_collected_count) for r in runs_with_metrics
            )
            cumulative_usable = sum(
                self._safe_int(r.usable_count) for r in runs_with_metrics
            )
            cumulative_quality_dropped = sum(
                self._safe_int(r.quality_dropped_count) for r in runs_with_metrics
            )
            cumulative_ranked = sum(
                self._safe_int(r.ranked_count) for r in runs_with_metrics
            )
            cumulative_duplicate_dropped = sum(
                self._safe_int(r.duplicate_dropped_count) for r in runs_with_metrics
            )
            cumulative_summaries = sum(
                self._safe_int(r.summaries_count) for r in runs_with_metrics
            )
            cumulative_inserted = sum(
                self._safe_int(r.inserted_count) for r in runs_with_metrics
            )
            cumulative_updated = sum(
                self._safe_int(r.updated_count) for r in runs_with_metrics
            )
            cumulative_candidates = sum(
                self._safe_int(r.summary_candidates_count) for r in runs_with_metrics
            )

            pipe_collected = cumulative_collected or collected_articles
            pipe_usable = cumulative_usable or pipe_collected
            pipe_ranked = cumulative_ranked or pipe_collected
            pipe_unique = cumulative_inserted or unique_articles
            pipe_summaries = cumulative_summaries or summaries
            pipe_candidates = cumulative_candidates or pipe_unique

            return {
                "data_source": "pipeline_run",
                "collected_articles": pipe_collected,
                "unique_articles": pipe_unique,
                "summaries": pipe_summaries,
                "quality_dropped_articles": cumulative_quality_dropped,
                "duplicate_articles": max(pipe_collected - pipe_unique, 0),
                "summary_candidates": pipe_candidates,
                "usable_articles": pipe_usable,
                "ranked_articles": pipe_ranked,
                "inserted_articles": cumulative_inserted,
                "updated_articles": cumulative_updated,
                "duplicate_dropped_articles": cumulative_duplicate_dropped,
                "has_data": pipe_collected > 0 or pipe_summaries > 0,
                "cache_reused": bool(
                    latest_run.used_cached_articles or latest_run.used_cached_summaries
                ),
            }

        return {"data_source": "derived" if collected_articles > 0 or summaries > 0 else "empty", **derived, "cache_reused": False}

    async def _build_runs_payload(
        self,
        session: AsyncSession,
        metrics_date: date,
    ) -> list[dict[str, Any]]:
        runs = await self._collection_runs_for_date(session, metrics_date)
        if not runs:
            return []

        result: list[dict[str, Any]] = []
        cumulative_briefs = 0
        for run in runs:
            if not any(
                self._safe_int(getattr(run, field, 0)) > 0
                for field in ("raw_collected_count", "usable_count", "inserted_count", "summaries_count")
            ):
                continue
            run_briefs = self._safe_int(run.summaries_count)
            cumulative_briefs += run_briefs
            result.append({
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "time": run.started_at.strftime("%H:%M") if run.started_at else "",
                "cache_reused": bool(run.used_cached_articles or run.used_cached_summaries),
                "briefs_count": run_briefs,
                "inserted_count": self._safe_int(run.inserted_count),
                "updated_count": self._safe_int(run.updated_count),
                "duplicate_dropped_count": self._safe_int(run.duplicate_dropped_count),
                "ranked_count": self._safe_int(run.ranked_count),
                "pipeline": [
                    {"label": "Recolectadas", "value": self._safe_int(run.raw_collected_count)},
                    {"label": "Utiles", "value": self._safe_int(run.usable_count)},
                    {"label": "Unicas", "value": self._safe_int(run.inserted_count)},
                    {"label": "Candidatas", "value": self._safe_int(run.summary_candidates_count)},
                    {"label": "Briefs", "value": cumulative_briefs},
                ],
            })
        return result

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

    async def _collection_runs_for_date(
        self,
        session: AsyncSession,
        metrics_date: date,
    ) -> list[CollectionRun]:
        start_at, end_at = self._day_bounds(metrics_date)
        stmt = (
            select(CollectionRun)
            .where(CollectionRun.started_at >= start_at, CollectionRun.started_at < end_at)
            .order_by(CollectionRun.started_at.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def _latest_impact_date(
        self,
        session: AsyncSession,
        before_or_on: date,
    ) -> date | None:
        _, end_at = self._day_bounds(before_or_on)
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
        inserted_articles: int = 0,
        updated_articles: int = 0,
        duplicate_dropped_articles: int = 0,
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
            "inserted_articles": max(int(inserted_articles), 0),
            "updated_articles": max(int(updated_articles), 0),
            "duplicate_dropped_articles": max(int(duplicate_dropped_articles), 0),
            "duplicate_articles_estimated": duplicate_articles_estimated,
            "reduction_rate": max(min(reduction_rate, 1.0), 0.0),
            "estimated_pages_avoided": estimated_pages_avoided,
            "estimated_minutes_saved": estimated_minutes_saved,
            "estimated_data_saved_mb": estimated_data_saved_mb,
            "cache_reused": cache_reused,
            "ai_calls_avoided_estimated": duplicate_articles_estimated,
            "pipeline": [
                {"label": "Recolectadas", "value": collected_articles},
                {"label": "Utiles", "value": max(int(usable_articles), 0)},
                {"label": "Unicas", "value": max(int(unique_articles), 0)},
                {"label": "Candidatas", "value": max(int(summary_candidates), 0)},
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
                        collected_at=_now_bolivia(),
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
        _, end_at = self._day_bounds(before_or_on)
        filters.append(NewsArticle.published_at < end_at)
        if exclude_summarized:
            filters.append(self._article_not_summarized_filter())

        stmt = (
            select(func.max(NewsArticle.published_at))
            .join(NewsCategory, NewsArticle.category_id == NewsCategory.id)
            .join(NewsSource, NewsArticle.source_id == NewsSource.id)
            .where(*filters)
        )
        max_pub = await session.scalar(stmt)
        if max_pub is None:
            return None
        return max_pub.date()

    def _day_bounds(self, value: date) -> tuple[datetime, datetime]:
        start = datetime(value.year, value.month, value.day)
        end = start + timedelta(days=1)
        return (start, end)

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
                elif article_id is not None:
                    existing_by_article = await self._get_summary_by_article(
                        session, article_id, summary_date
                    )
                    if existing_by_article:
                        existing_by_article.category_id = category.id
                        existing_by_article.title = title
                        existing_by_article.summary = body
                        existing_by_article.fact = fact
                        existing_by_article.llm_provider = llm_provider
                        existing_by_article.llm_model = llm_model
                        existing_by_article.story_cluster_id = story_cluster_id
                        existing_by_article.source_article_count = source_article_count
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
        start_at, end_at = self._day_bounds(summary_date)

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
                    NewsArticle.published_at >= start_at,
                    NewsArticle.published_at < end_at,
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

    async def get_worldcup_matches(self, match_date: date | None = None) -> list[dict]:
        async with self.session_maker() as session:
            stmt = select(WorldCupMatch).order_by(WorldCupMatch.match_date, WorldCupMatch.match_time)
            if match_date:
                stmt = stmt.where(WorldCupMatch.match_date == match_date)
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "match_date": r.match_date.isoformat(),
                "match_time": r.match_time.strftime("%H:%M"),
                "group": r.group_name,
                "home_team": r.home_team,
                "away_team": r.away_team,
                "home_flag": r.home_flag,
                "away_flag": r.away_flag,
                "home_score": r.home_score,
                "away_score": r.away_score,
                "is_playing": r.is_playing,
                "is_finished": r.is_finished,
                "stage": r.stage,
                "venue": r.venue,
            }
            for r in rows
        ]

    async def start_match(self, match_id: int) -> dict | None:
        async with self.session_maker() as session:
            stmt = select(WorldCupMatch).where(WorldCupMatch.id == match_id)
            result = await session.execute(stmt)
            match = result.scalar_one_or_none()
            if not match:
                return None
            match.is_playing = True
            match.is_finished = False
            await session.commit()
            return {"id": match.id, "is_playing": match.is_playing, "is_finished": match.is_finished}

    async def update_match_score(self, match_id: int, home_score: int, away_score: int) -> dict | None:
        async with self.session_maker() as session:
            stmt = select(WorldCupMatch).where(WorldCupMatch.id == match_id)
            result = await session.execute(stmt)
            match = result.scalar_one_or_none()
            if not match:
                return None
            match.home_score = home_score
            match.away_score = away_score
            await session.commit()
            return {
                "id": match.id,
                "home_team": match.home_team,
                "away_team": match.away_team,
                "home_score": match.home_score,
                "away_score": match.away_score,
            }

    async def finish_match(self, match_id: int) -> dict | None:
        async with self.session_maker() as session:
            stmt = select(WorldCupMatch).where(WorldCupMatch.id == match_id)
            result = await session.execute(stmt)
            match = result.scalar_one_or_none()
            if not match:
                return None
            if not match.is_playing:
                raise ValueError("El partido no está en juego")
            match.is_playing = False
            match.is_finished = True
            await session.commit()
            return {
                "id": match.id,
                "is_playing": match.is_playing,
                "is_finished": match.is_finished,
            }

    async def close(self):
        """Cierra el pool de conexiones."""
        await self.engine.dispose()
        logger.info("Database cerrada")

    @staticmethod
    def _gmt_to_bolivia(gmt_date: date, gmt_time: time) -> tuple[date, time]:
        dt = datetime.combine(gmt_date, gmt_time) - timedelta(hours=4)
        return dt.date(), dt.time()

    async def _seed_worldcup_matches(self, session: AsyncSession) -> None:
        stmt = select(func.count(WorldCupMatch.id))
        result = await session.execute(stmt)
        if result.scalar() > 0:
            return

        # (gmt_date, gmt_time, group, home, away, home_flag, away_flag, venue)
        raw: list[tuple[date, time, str, str, str, str, str, str]] = [
            # Group A
            (date(2026, 6, 11), time(19, 0), "A", "México", "Sudáfrica", "🇲🇽", "🇿🇦", "Mexico City Stadium"),
            (date(2026, 6, 12), time(2, 0), "A", "Corea del Sur", "República Checa", "🇰🇷", "🇨🇿", "Estadio Guadalajara"),
            (date(2026, 6, 18), time(16, 0), "A", "República Checa", "Sudáfrica", "🇨🇿", "🇿🇦", "Atlanta Stadium"),
            (date(2026, 6, 19), time(1, 0), "A", "México", "Corea del Sur", "🇲🇽", "🇰🇷", "Estadio Guadalajara"),
            (date(2026, 6, 25), time(1, 0), "A", "República Checa", "México", "🇨🇿", "🇲🇽", "Mexico City Stadium"),
            (date(2026, 6, 25), time(1, 0), "A", "Sudáfrica", "Corea del Sur", "🇿🇦", "🇰🇷", "Estadio Monterrey"),
            # Group B
            (date(2026, 6, 12), time(19, 0), "B", "Canadá", "Bosnia y Herzegovina", "🇨🇦", "🇧🇦", "Toronto Stadium"),
            (date(2026, 6, 13), time(19, 0), "B", "Catar", "Suiza", "🇶🇦", "🇨🇭", "San Francisco Bay Area Stadium"),
            (date(2026, 6, 18), time(19, 0), "B", "Suiza", "Bosnia y Herzegovina", "🇨🇭", "🇧🇦", "Los Angeles Stadium"),
            (date(2026, 6, 18), time(22, 0), "B", "Canadá", "Catar", "🇨🇦", "🇶🇦", "BC Place Vancouver"),
            (date(2026, 6, 24), time(19, 0), "B", "Suiza", "Canadá", "🇨🇭", "🇨🇦", "BC Place Vancouver"),
            (date(2026, 6, 24), time(19, 0), "B", "Bosnia y Herzegovina", "Catar", "🇧🇦", "🇶🇦", "Seattle Stadium"),
            # Group C
            (date(2026, 6, 13), time(22, 0), "C", "Brasil", "Marruecos", "🇧🇷", "🇲🇦", "New York New Jersey Stadium"),
            (date(2026, 6, 14), time(1, 0), "C", "Haití", "Escocia", "🇭🇹", "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Boston Stadium"),
            (date(2026, 6, 19), time(22, 0), "C", "Escocia", "Marruecos", "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "🇲🇦", "Boston Stadium"),
            (date(2026, 6, 20), time(1, 0), "C", "Brasil", "Haití", "🇧🇷", "🇭🇹", "Philadelphia Stadium"),
            (date(2026, 6, 24), time(22, 0), "C", "Escocia", "Brasil", "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "🇧🇷", "Miami Stadium"),
            (date(2026, 6, 24), time(22, 0), "C", "Marruecos", "Haití", "🇲🇦", "🇭🇹", "Atlanta Stadium"),
            # Group D
            (date(2026, 6, 13), time(1, 0), "D", "Estados Unidos", "Paraguay", "🇺🇸", "🇵🇾", "Los Angeles Stadium"),
            (date(2026, 6, 14), time(4, 0), "D", "Australia", "Turquía", "🇦🇺", "🇹🇷", "BC Place Vancouver"),
            (date(2026, 6, 19), time(19, 0), "D", "Estados Unidos", "Australia", "🇺🇸", "🇦🇺", "Seattle Stadium"),
            (date(2026, 6, 20), time(4, 0), "D", "Turquía", "Paraguay", "🇹🇷", "🇵🇾", "San Francisco Bay Area Stadium"),
            (date(2026, 6, 26), time(2, 0), "D", "Turquía", "Estados Unidos", "🇹🇷", "🇺🇸", "Los Angeles Stadium"),
            (date(2026, 6, 26), time(2, 0), "D", "Paraguay", "Australia", "🇵🇾", "🇦🇺", "San Francisco Bay Area Stadium"),
            # Group E
            (date(2026, 6, 14), time(17, 0), "E", "Alemania", "Curazao", "🇩🇪", "🇨🇼", "Houston Stadium"),
            (date(2026, 6, 14), time(23, 0), "E", "Costa de Marfil", "Ecuador", "🇨🇮", "🇪🇨", "Philadelphia Stadium"),
            (date(2026, 6, 20), time(20, 0), "E", "Alemania", "Costa de Marfil", "🇩🇪", "🇨🇮", "Toronto Stadium"),
            (date(2026, 6, 21), time(0, 0), "E", "Ecuador", "Curazao", "🇪🇨", "🇨🇼", "Kansas City Stadium"),
            (date(2026, 6, 25), time(20, 0), "E", "Ecuador", "Alemania", "🇪🇨", "🇩🇪", "New York New Jersey Stadium"),
            (date(2026, 6, 25), time(20, 0), "E", "Curazao", "Costa de Marfil", "🇨🇼", "🇨🇮", "Philadelphia Stadium"),
            # Group F
            (date(2026, 6, 14), time(20, 0), "F", "Países Bajos", "Japón", "🇳🇱", "🇯🇵", "Dallas Stadium"),
            (date(2026, 6, 15), time(4, 0), "F", "Suecia", "Túnez", "🇸🇪", "🇹🇳", "Estadio Monterrey"),
            (date(2026, 6, 20), time(17, 0), "F", "Países Bajos", "Suecia", "🇳🇱", "🇸🇪", "Houston Stadium"),
            (date(2026, 6, 21), time(4, 0), "F", "Túnez", "Japón", "🇹🇳", "🇯🇵", "Estadio Monterrey"),
            (date(2026, 6, 25), time(23, 0), "F", "Japón", "Suecia", "🇯🇵", "🇸🇪", "Dallas Stadium"),
            (date(2026, 6, 25), time(23, 0), "F", "Túnez", "Países Bajos", "🇹🇳", "🇳🇱", "Kansas City Stadium"),
            # Group G
            (date(2026, 6, 15), time(19, 0), "G", "Bélgica", "Egipto", "🇧🇪", "🇪🇬", "BC Place Vancouver"),
            (date(2026, 6, 16), time(1, 0), "G", "Irán", "Nueva Zelanda", "🇮🇷", "🇳🇿", "Los Angeles Stadium"),
            (date(2026, 6, 21), time(19, 0), "G", "Bélgica", "Irán", "🇧🇪", "🇮🇷", "Los Angeles Stadium"),
            (date(2026, 6, 22), time(1, 0), "G", "Nueva Zelanda", "Egipto", "🇳🇿", "🇪🇬", "BC Place Vancouver"),
            (date(2026, 6, 27), time(3, 0), "G", "Egipto", "Irán", "🇪🇬", "🇮🇷", "Seattle Stadium"),
            (date(2026, 6, 27), time(3, 0), "G", "Nueva Zelanda", "Bélgica", "🇳🇿", "🇧🇪", "BC Place Vancouver"),
            # Group H
            (date(2026, 6, 15), time(16, 0), "H", "España", "Cabo Verde", "🇪🇸", "🇨🇻", "Atlanta Stadium"),
            (date(2026, 6, 15), time(22, 0), "H", "Arabia Saudita", "Uruguay", "🇸🇦", "🇺🇾", "Miami Stadium"),
            (date(2026, 6, 21), time(16, 0), "H", "España", "Arabia Saudita", "🇪🇸", "🇸🇦", "Atlanta Stadium"),
            (date(2026, 6, 21), time(22, 0), "H", "Uruguay", "Cabo Verde", "🇺🇾", "🇨🇻", "Miami Stadium"),
            (date(2026, 6, 27), time(0, 0), "H", "Cabo Verde", "Arabia Saudita", "🇨🇻", "🇸🇦", "Houston Stadium"),
            (date(2026, 6, 27), time(0, 0), "H", "Uruguay", "España", "🇺🇾", "🇪🇸", "Estadio Guadalajara"),
            # Group I
            (date(2026, 6, 16), time(19, 0), "I", "Francia", "Senegal", "🇫🇷", "🇸🇳", "New York New Jersey Stadium"),
            (date(2026, 6, 16), time(22, 0), "I", "Irak", "Noruega", "🇮🇶", "🇳🇴", "Boston Stadium"),
            (date(2026, 6, 22), time(21, 0), "I", "Francia", "Irak", "🇫🇷", "🇮🇶", "Philadelphia Stadium"),
            (date(2026, 6, 23), time(0, 0), "I", "Noruega", "Senegal", "🇳🇴", "🇸🇳", "New York New Jersey Stadium"),
            (date(2026, 6, 26), time(19, 0), "I", "Noruega", "Francia", "🇳🇴", "🇫🇷", "Boston Stadium"),
            (date(2026, 6, 26), time(19, 0), "I", "Senegal", "Irak", "🇸🇳", "🇮🇶", "Toronto Stadium"),
            # Group J
            (date(2026, 6, 17), time(1, 0), "J", "Argentina", "Argelia", "🇦🇷", "🇩🇿", "Kansas City Stadium"),
            (date(2026, 6, 17), time(4, 0), "J", "Austria", "Jordania", "🇦🇹", "🇯🇴", "San Francisco Bay Area Stadium"),
            (date(2026, 6, 22), time(17, 0), "J", "Argentina", "Austria", "🇦🇷", "🇦🇹", "Dallas Stadium"),
            (date(2026, 6, 23), time(3, 0), "J", "Jordania", "Argelia", "🇯🇴", "🇩🇿", "San Francisco Bay Area Stadium"),
            (date(2026, 6, 28), time(2, 0), "J", "Argelia", "Austria", "🇩🇿", "🇦🇹", "Kansas City Stadium"),
            (date(2026, 6, 28), time(2, 0), "J", "Jordania", "Argentina", "🇯🇴", "🇦🇷", "Dallas Stadium"),
            # Group K
            (date(2026, 6, 17), time(17, 0), "K", "Portugal", "RD Congo", "🇵🇹", "🇨🇩", "Houston Stadium"),
            (date(2026, 6, 18), time(2, 0), "K", "Uzbekistán", "Colombia", "🇺🇿", "🇨🇴", "Mexico City Stadium"),
            (date(2026, 6, 23), time(17, 0), "K", "Portugal", "Uzbekistán", "🇵🇹", "🇺🇿", "Houston Stadium"),
            (date(2026, 6, 24), time(2, 0), "K", "Colombia", "RD Congo", "🇨🇴", "🇨🇩", "Estadio Guadalajara"),
            (date(2026, 6, 27), time(23, 30), "K", "Colombia", "Portugal", "🇵🇹", "Miami Stadium"),
            (date(2026, 6, 27), time(23, 30), "K", "RD Congo", "Uzbekistán", "🇨🇩", "🇺🇿", "Atlanta Stadium"),
            # Group L
            (date(2026, 6, 17), time(20, 0), "L", "Inglaterra", "Croacia", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "🇭🇷", "Dallas Stadium"),
            (date(2026, 6, 17), time(23, 0), "L", "Ghana", "Panamá", "🇬🇭", "🇵🇦", "Toronto Stadium"),
            (date(2026, 6, 23), time(20, 0), "L", "Inglaterra", "Ghana", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "🇬🇭", "Boston Stadium"),
            (date(2026, 6, 23), time(23, 0), "L", "Panamá", "Croacia", "🇵🇦", "🇭🇷", "Toronto Stadium"),
            (date(2026, 6, 27), time(21, 0), "L", "Panamá", "Inglaterra", "🇵🇦", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "New York New Jersey Stadium"),
            (date(2026, 6, 27), time(21, 0), "L", "Croacia", "Ghana", "🇭🇷", "🇬🇭", "Philadelphia Stadium"),
        ]

        for gmt_date, gmt_time, group, home, away, hf, af, venue in raw:
            bolivia_date, bolivia_time = self._gmt_to_bolivia(gmt_date, gmt_time)
            session.add(WorldCupMatch(
                match_date=bolivia_date,
                match_time=bolivia_time,
                group_name=group,
                home_team=home,
                away_team=away,
                home_flag=hf,
                away_flag=af,
                venue=venue,
                stage="group",
            ))
        logger.info(f"Semillados {len(raw)} partidos de fase de grupos")

        # Round of 32 (16avos de final)
        # (gmt_date, gmt_time, group, home, away, home_flag, away_flag, venue)
        raw_r32: list[tuple[date, time, str, str, str, str, str, str]] = [
            # Dom 28 jun
            (date(2026, 6, 28), time(19, 0), "KO", "Sudáfrica", "Canadá", "🇿🇦", "🇨🇦", "Los Angeles Stadium"),
            # Lun 29 jun
            (date(2026, 6, 29), time(17, 0), "KO", "Brasil", "Japón", "🇧🇷", "🇯🇵", "Houston Stadium"),
            (date(2026, 6, 29), time(20, 30), "KO", "Alemania", "Paraguay", "🇩🇪", "🇵🇾", "Boston Stadium"),
            (date(2026, 6, 30), time(1, 0), "KO", "Países Bajos", "Marruecos", "🇳🇱", "🇲🇦", "Estadio Monterrey"),
            # Mar 30 jun
            (date(2026, 6, 30), time(17, 0), "KO", "Costa de Marfil", "Noruega", "🇨🇮", "🇳🇴", "Dallas Stadium"),
            (date(2026, 6, 30), time(21, 0), "KO", "Francia", "Suecia", "🇫🇷", "🇸🇪", "New York New Jersey Stadium"),
            (date(2026, 7, 1), time(1, 0), "KO", "México", "Ecuador", "🇲🇽", "🇪🇨", "Estadio Ciudad de México"),
            # Mié 1 jul
            (date(2026, 7, 1), time(16, 0), "KO", "Inglaterra", "RD Congo", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "🇨🇩", "Atlanta Stadium"),
            (date(2026, 7, 1), time(20, 0), "KO", "Bélgica", "Senegal", "🇧🇪", "🇸🇳", "Seattle Stadium"),
            (date(2026, 7, 2), time(0, 0), "KO", "Estados Unidos", "Bosnia y Herzegovina", "🇺🇸", "🇧🇦", "San Francisco Bay Area Stadium"),
            # Jue 2 jul
            (date(2026, 7, 2), time(19, 0), "KO", "España", "Austria", "🇪🇸", "🇦🇹", "Los Angeles Stadium"),
            (date(2026, 7, 2), time(23, 0), "KO", "Portugal", "Croacia", "🇵🇹", "🇭🇷", "Toronto Stadium"),
            (date(2026, 7, 3), time(3, 0), "KO", "Suiza", "Argelia", "🇨🇭", "🇩🇿", "BC Place Vancouver"),
            # Vie 3 jul
            (date(2026, 7, 3), time(18, 0), "KO", "Australia", "Egipto", "🇦🇺", "🇪🇬", "Dallas Stadium"),
            (date(2026, 7, 3), time(22, 0), "KO", "Argentina", "Cabo Verde", "🇦🇷", "🇨🇻", "Miami Stadium"),
            (date(2026, 7, 4), time(1, 30), "KO", "Colombia", "Ghana", "🇨🇴", "🇬🇭", "Kansas City Stadium"),
        ]

        for gmt_date, gmt_time, group, home, away, hf, af, venue in raw_r32:
            bolivia_date, bolivia_time = self._gmt_to_bolivia(gmt_date, gmt_time)
            session.add(WorldCupMatch(
                match_date=bolivia_date,
                match_time=bolivia_time,
                group_name=group,
                home_team=home,
                away_team=away,
                home_flag=hf,
                away_flag=af,
                venue=venue,
                stage="round_32",
            ))
        logger.info(f"Semillados {len(raw_r32)} partidos de 16avos de final")

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
            source.updated_at = _now_bolivia()
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

    async def _get_summary_by_article(
        self,
        session: AsyncSession,
        article_id: int,
        summary_date: date,
    ) -> NewsSummary | None:
        stmt = select(NewsSummary).where(
            NewsSummary.article_id == article_id,
            NewsSummary.summary_date == summary_date,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_article_ids_with_summaries(
        self,
        article_ids: list[int],
    ) -> set[int]:
        if not article_ids:
            return set()
        async with self.session_maker() as session:
            result = await session.execute(
                select(NewsSummary.article_id).where(
                    NewsSummary.article_id.in_(article_ids),
                )
            )
            return {row[0] for row in result.all()}

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

    @staticmethod
    def _format_datetime(value: date | datetime | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.isoformat() + "-04:00"
            return value.isoformat()
        return value.isoformat()

    def _coerce_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value.replace(tzinfo=None) if value.tzinfo else value
        return _now_bolivia()

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
            "published_at": self._format_datetime(article.published_at),
            "collected_at": self._format_datetime(article.collected_at),
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
            "published_at": self._format_datetime(published_at),
            "image": image_url,
            "article_description": article_description,
            "llm_provider": summary.llm_provider,
            "llm_model": summary.llm_model,
            "summary_date": self._format_datetime(summary.summary_date),
            "created_at": self._format_datetime(summary.created_at),
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
