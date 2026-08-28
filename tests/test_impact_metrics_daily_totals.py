"""Regression tests for the /impacto page showing inflated numbers on days
with multiple pipeline runs.

get_impact_metrics used to sum raw_collected_count/summaries_count/etc.
across every CollectionRun of the day. Each run re-scrapes mostly the same
articles, so that sum doesn't represent distinct articles -- confirmed live
on a day with 9 runs: the page said "1819 recolectadas" when the DB actually
had 185 distinct articles published that day. Totals for
collected/unique/summaries now come from real DB counts; only the
flow-only stages that have no DB equivalent (usable/candidates/ranked/
dropped, which are never persisted for rejected articles) fall back to the
most recent run's own numbers instead of a summed total.
"""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.repository import (
    Base,
    CollectionRun,
    Database,
    NewsArticle,
    NewsCategory,
    NewsSource,
    NewsSummary,
)


@pytest.fixture
async def db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    database = object.__new__(Database)
    database.engine = engine
    database.session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield database
    await engine.dispose()


@pytest.mark.asyncio
async def test_daily_totals_use_real_counts_not_the_sum_of_repeated_runs(db: Database):
    async with db.session_maker() as session:
        category = NewsCategory(name="general", display_name="General")
        source = NewsSource(name="Fuente", source_type="scraper")
        session.add_all([category, source])
        await session.flush()

        day = datetime(2026, 8, 27, 9, 0, 0)
        for i in range(3):
            session.add(NewsArticle(
                title=f"Articulo {i}",
                url=f"https://example.com/{i}",
                url_hash=f"https://example.com/{i}",
                category_id=category.id,
                source_id=source.id,
                published_at=day,
                collected_at=day,
                is_active=True,
            ))
        session.add(NewsSummary(
            category_id=category.id,
            title="Resumen unico del dia",
            summary="Resumen valido.",
            summary_date=date(2026, 8, 27),
            created_at=day,
        ))

        # Tres corridas del mismo dia, cada una re-scrapeando casi lo mismo
        # (como pasa en la realidad: el mismo puñado de sitios, varias veces
        # al dia). Si se suman estos raw_collected_count, "recolectadas" da
        # 600 -- muy por encima de los 3 articulos reales que quedaron en la
        # base para ese dia.
        for i in range(3):
            session.add(CollectionRun(
                started_at=day + timedelta(hours=i),
                finished_at=day + timedelta(hours=i, minutes=5),
                status="success",
                raw_collected_count=200,
                usable_count=150,
                quality_dropped_count=10,
                inserted_count=1,
                updated_count=1,
                ranked_count=140,
                summary_candidates_count=30,
                summaries_count=1,
                duplicate_dropped_count=2,
            ))
        await session.commit()

    metrics = await db.get_impact_metrics(date(2026, 8, 27), fallback_to_latest=False)

    assert metrics["collected_articles"] == 3
    assert metrics["unique_articles"] == 3
    assert metrics["summaries"] == 1
    # Estas si vienen de la corrida mas reciente (no hay verdad en la DB
    # para "cuantas pasaron el filtro de calidad", ya que las rechazadas
    # nunca se guardan) -- 150, no 450.
    assert metrics["usable_articles"] == 150
    assert metrics["summary_candidates"] == 30
    assert metrics["ranked_articles"] == 140
    assert metrics["quality_dropped_articles"] == 10
    assert metrics["duplicate_dropped_articles"] == 2
    # inserted/updated si son deltas legitimos por corrida -- sumar esos no
    # duplica nada, cada URL solo se inserta una vez.
    assert metrics["inserted_articles"] == 3
    assert metrics["updated_articles"] == 3
