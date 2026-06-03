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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

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
    channel = Column(String(20), nullable=False, default="whatsapp")
    categories = Column(JSON, nullable=False, default=list)
    timezone = Column(String(50), nullable=False, default="America/La_Paz")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    is_active = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Subscriber {self.phone or self.telegram_id} active={self.is_active}>"


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
    error_message = Column(Text, nullable=True)


class NewsSummary(Base):
    __tablename__ = "news_summaries"
    __table_args__ = (
        UniqueConstraint("category_id", "summary_date", "title", name="uq_summary_day_title"),
    )

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("news_articles.id"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("news_categories.id"), nullable=False, index=True)
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
    IMPACT_METHODOLOGY_NOTE = (
        "Estimaciones orientativas basadas en articulos evitados, no medicion energetica directa."
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
            await conn.run_sync(Base.metadata.create_all)

        async with self.session_maker() as session:
            await self._seed_categories(session)
            await session.commit()

        logger.info("Tablas creadas")

    async def save_subscription(
        self,
        phone: str | None = None,
        telegram_id: str | None = None,
        channel: str = "whatsapp",
        categories: set[str] | None = None,
    ) -> bool:
        """Guarda o actualiza una suscripcion."""

        if not phone and not telegram_id:
            logger.error("Se requiere phone o telegram_id")
            return False

        async with self.session_maker() as session:
            subscriber = await self._find_subscriber(session, phone, telegram_id)

            if subscriber:
                if categories:
                    subscriber.categories = sorted(categories)
                subscriber.channel = channel
                subscriber.updated_at = datetime.utcnow()
                subscriber.is_active = True
                logger.info(f"Actualizada suscripcion: {phone or telegram_id}")
            else:
                subscriber = Subscriber(
                    phone=phone,
                    telegram_id=telegram_id,
                    channel=channel,
                    categories=sorted(categories) if categories else ["general"],
                )
                session.add(subscriber)
                logger.info(f"Nueva suscripcion: {phone or telegram_id}")

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
                )
                .values(is_active=False, updated_at=datetime.utcnow())
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
        collected_from_run = (
            int((latest_run.scraper_count or 0) + (latest_run.newsapi_count or 0))
            if latest_run
            else 0
        )
        collected_articles = max(collected_from_run, unique_articles)

        return {
            "collected_articles": collected_articles,
            "unique_articles": unique_articles,
            "summaries": summaries,
            "cache_reused": False,
            "has_data": collected_articles > 0 or unique_articles > 0 or summaries > 0,
        }

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
    ) -> dict[str, Any]:
        collected_articles = max(int(collected_articles), 0)
        unique_articles = max(int(unique_articles), 0)
        summaries = max(int(summaries), 0)
        duplicate_articles_estimated = max(collected_articles - unique_articles, 0)
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
            "collected_articles": collected_articles,
            "unique_articles": unique_articles,
            "summaries": summaries,
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
                payload = self._normalize_payload(article)
                published_at = self._coerce_datetime(article.get("published_at"))
                score = self._coerce_score(article.get("score"))

                if existing:
                    article["id"] = existing.id
                    existing.title = title
                    existing.url = url
                    existing.description = article.get("description")
                    existing.content = article.get("content")
                    existing.author = article.get("author")
                    existing.image_url = article.get("image")
                    existing.source_id = source.id
                    existing.category_id = category.id
                    existing.country = article.get("country")
                    existing.published_at = published_at
                    existing.collected_at = datetime.utcnow()
                    existing.raw_payload = payload
                    existing.score = score
                    existing.is_active = True
                    updated += 1
                else:
                    news_article = NewsArticle(
                        title=title,
                        url=url,
                        url_hash=url_hash,
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

        return {"inserted": inserted, "updated": updated}

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
        summary_date_filter = article_date if article_date is not None else func.date(NewsArticle.published_at)
        summarized_article_exists = exists().where(
            NewsSummary.article_id == NewsArticle.id,
            NewsSummary.summary_date == summary_date_filter,
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

    async def save_summaries(
        self,
        summaries: list[dict],
        *,
        llm_provider: str | None = None,
        llm_model: str | None = None,
    ) -> dict[str, int]:
        inserted = 0
        updated = 0
        summary_date = date.today()

        async with self.session_maker() as session:
            category_cache: dict[str, NewsCategory] = {}

            for summary in summaries:
                title = str(summary.get("title") or "").strip()
                body = str(summary.get("summary") or "").strip()
                category_name = str(summary.get("category") or "general").strip().lower()
                if not title or not body:
                    continue

                category = await self._get_or_create_category(
                    session, category_name, category_cache
                )
                article_id = summary.get("article_id")
                fact = summary.get("fact")

                existing = await self._get_summary(session, category.id, summary_date, title)
                if existing:
                    existing.summary = body
                    existing.fact = fact
                    existing.llm_provider = llm_provider
                    existing.llm_model = llm_model
                    existing.article_id = article_id
                    updated += 1
                else:
                    session.add(
                        NewsSummary(
                            article_id=article_id,
                            category_id=category.id,
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
                )
                .join(NewsCategory, NewsSummary.category_id == NewsCategory.id)
                .outerjoin(NewsArticle, NewsSummary.article_id == NewsArticle.id)
                .outerjoin(NewsSource, NewsArticle.source_id == NewsSource.id)
                .where(
                    NewsCategory.name.in_(categories),
                    NewsSummary.summary_date == summary_date,
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
        filters = [NewsSummary.summary_date == summary_date]
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
    ) -> Subscriber | None:
        filters = []
        if phone:
            filters.append(Subscriber.phone == phone)
        if telegram_id:
            filters.append(Subscriber.telegram_id == telegram_id)

        if not filters:
            return None

        stmt = select(Subscriber).where(or_(*filters))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
