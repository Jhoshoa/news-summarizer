"""Tests for two story-clustering/deduplication fixes:

1. find_recent_story_match ya no exige category_id igual antes de comparar
   candidatos por similitud (antes, dos articulos del mismo hecho clasificados
   en categorias distintas por distintas fuentes nunca se comparaban).
2. link_ai_detected_duplicates persiste en la DB los duplicados que detecta
   AIStoryDeduplicator, para que el listado/detalle los trate como una sola
   historia (antes, la deduplicacion por IA solo afectaba que se resumiera,
   sin dejar rastro en story_cluster_id/duplicate_of_article_id).
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.repository import Base, Database, NewsArticle, NewsCategory, NewsSource, Story, StoryArticle


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


async def _seed_category_and_source(session, *, category_name="general", source_name="Fuente"):
    category = NewsCategory(name=category_name, display_name=category_name.capitalize())
    source = NewsSource(name=source_name, source_type="scraper")
    session.add_all([category, source])
    await session.flush()
    return category, source


async def _make_article(
    session,
    *,
    category_id: int,
    source_id: int,
    title: str,
    url: str,
    story_cluster_id: str,
    published_at: datetime,
) -> NewsArticle:
    article = NewsArticle(
        title=title,
        url=url,
        url_hash=url,
        canonical_key=title,
        content_fingerprint=f"fp-{url}",
        story_cluster_id=story_cluster_id,
        category_id=category_id,
        source_id=source_id,
        published_at=published_at,
        collected_at=published_at,
        is_active=True,
    )
    session.add(article)
    await session.flush()
    return article


@pytest.mark.asyncio
async def test_find_recent_story_match_compares_across_categories(db: Database):
    """Dos articulos casi identicos en categorias distintas deben poder
    matchear por contenido: antes, el filtro category_id == category_id se lo
    impedia por completo, sin importar cuan alta fuera la similitud."""

    async with db.session_maker() as session:
        category_general, source = await _seed_category_and_source(session, category_name="general")
        category_policiales = NewsCategory(name="policiales", display_name="Policiales")
        session.add(category_policiales)
        await session.flush()

        now = datetime(2026, 8, 26, 12, 0, 0)
        existing = await _make_article(
            session,
            category_id=category_policiales.id,
            source_id=source.id,
            title="Al menos 98 fallecidos por la riada en Nepal",
            url="https://example.com/nepal-1",
            story_cluster_id="cluster-nepal",
            published_at=now,
        )
        await session.commit()

        new_article = {
            "title": "Al menos 98 fallecidos por la riada en Nepal",
            "description": "Al menos 98 fallecidos por la riada en Nepal, segun reportes.",
            "category": "general",
        }
        match = await db.find_recent_story_match(
            session,
            new_article,
            category_id=category_general.id,
            published_at=now + timedelta(minutes=5),
        )

    assert match is not None
    matched_article, reason, score = match
    assert matched_article.id == existing.id
    assert reason in ("fingerprint", "title_similarity", "content_similarity")
    assert score >= db.STORY_SIMILARITY_THRESHOLD


@pytest.mark.asyncio
async def test_find_recent_story_match_still_respects_similarity_threshold(db: Database):
    """Ampliar el pool de candidatos no debe convertirse en un falso positivo:
    dos titulares sin relacion, en categorias distintas, no deben matchear."""

    async with db.session_maker() as session:
        category_general, source = await _seed_category_and_source(session, category_name="general")
        category_deportes = NewsCategory(name="deportes", display_name="Deportes")
        session.add(category_deportes)
        await session.flush()

        now = datetime(2026, 8, 26, 12, 0, 0)
        await _make_article(
            session,
            category_id=category_deportes.id,
            source_id=source.id,
            title="Bolivar gana 2-0 y clasifica a la final",
            url="https://example.com/futbol-1",
            story_cluster_id="cluster-futbol",
            published_at=now,
        )
        await session.commit()

        new_article = {
            "title": "Gobierno anuncia nueva medida economica para el agro",
            "description": "El ministerio de economia detallo la nueva medida para el sector agropecuario.",
            "category": "general",
        }
        match = await db.find_recent_story_match(
            session,
            new_article,
            category_id=category_general.id,
            published_at=now + timedelta(minutes=5),
        )

    assert match is None


@pytest.mark.asyncio
async def test_link_ai_detected_duplicates_merges_singleton_cluster(db: Database):
    async with db.session_maker() as session:
        category, source_a = await _seed_category_and_source(session, source_name="RedUno")
        source_b = NewsSource(name="Unitel", source_type="scraper")
        session.add(source_b)
        await session.flush()

        now = datetime(2026, 8, 26, 18, 0, 0)
        primary = await _make_article(
            session,
            category_id=category.id,
            source_id=source_a.id,
            title="Paz rompe el silencio sobre Cerimedo",
            url="https://example.com/paz-1",
            story_cluster_id="cluster-a",
            published_at=now,
        )
        duplicate = await _make_article(
            session,
            category_id=category.id,
            source_id=source_b.id,
            title="Paz: Cerimedo jamas tuvo autorizacion",
            url="https://example.com/paz-2",
            story_cluster_id="cluster-b",
            published_at=now,
        )
        session.add(Story(
            id="cluster-a", canonical_title=primary.title, category="politica",
            country="BO", first_published_at=now, last_updated_at=now,
            article_count=1, source_count=1,
        ))
        session.add(Story(
            id="cluster-b", canonical_title=duplicate.title, category="politica",
            country="BO", first_published_at=now, last_updated_at=now,
            article_count=1, source_count=1,
        ))
        session.add(StoryArticle(story_id="cluster-a", article_id=primary.id))
        session.add(StoryArticle(story_id="cluster-b", article_id=duplicate.id))
        await session.commit()
        primary_id, duplicate_id = primary.id, duplicate.id

    await db.link_ai_detected_duplicates(primary_id, [duplicate_id])

    async with db.session_maker() as session:
        refreshed_duplicate = await session.get(NewsArticle, duplicate_id)
        assert refreshed_duplicate.story_cluster_id == "cluster-a"
        assert refreshed_duplicate.duplicate_of_article_id == primary_id
        assert refreshed_duplicate.duplicate_reason == "ai_semantic"

        old_story = await session.get(Story, "cluster-b")
        assert old_story is None

        primary_story = await session.get(Story, "cluster-a")
        assert primary_story.article_count == 2
        assert primary_story.source_count == 2

        link = await session.get(StoryArticle, {"story_id": "cluster-a", "article_id": duplicate_id})
        assert link is not None
        assert link.relationship_type == "duplicate"


@pytest.mark.asyncio
async def test_link_ai_detected_duplicates_skips_non_singleton_cluster(db: Database):
    """Si el 'duplicado' ya tiene hermanos en su propio cluster, no se fusiona
    automaticamente (fusionar clusters completos no es seguro de inferir solo
    de una decision del LLM sobre un articulo puntual)."""

    async with db.session_maker() as session:
        category, source = await _seed_category_and_source(session)
        now = datetime(2026, 8, 26, 12, 0, 0)
        primary = await _make_article(
            session, category_id=category.id, source_id=source.id,
            title="Primario", url="https://example.com/1",
            story_cluster_id="cluster-a", published_at=now,
        )
        duplicate = await _make_article(
            session, category_id=category.id, source_id=source.id,
            title="Duplicado", url="https://example.com/2",
            story_cluster_id="cluster-b", published_at=now,
        )
        sibling = await _make_article(
            session, category_id=category.id, source_id=source.id,
            title="Hermano del duplicado", url="https://example.com/3",
            story_cluster_id="cluster-b", published_at=now,
        )
        await session.commit()
        primary_id, duplicate_id = primary.id, duplicate.id

    await db.link_ai_detected_duplicates(primary_id, [duplicate_id])

    async with db.session_maker() as session:
        refreshed_duplicate = await session.get(NewsArticle, duplicate_id)
        assert refreshed_duplicate.story_cluster_id == "cluster-b"
        assert refreshed_duplicate.duplicate_of_article_id is None


@pytest.mark.asyncio
async def test_link_ai_detected_duplicates_noop_without_duplicates(db: Database):
    await db.link_ai_detected_duplicates(1, [])
