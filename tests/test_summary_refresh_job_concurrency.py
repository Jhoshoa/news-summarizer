"""Tests for get_active_summary_refresh_job, the DB-backed guard against
overlapping /trigger/summary runs (see tests/test_private_refresh_endpoints.py
for the endpoint-level behavior). A real DB is used here (not the fake in
test_private_refresh_endpoints.py) because the interesting logic --
filtering by status and by staleness -- lives in the SQL query itself."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.repository import Base, Database, SummaryRefreshJob


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


async def _insert_job(db: Database, *, job_id: str, status: str, requested_at: datetime):
    async with db.session_maker() as session:
        session.add(
            SummaryRefreshJob(
                id=job_id,
                status=status,
                time_of_day="manual",
                refresh=True,
                requested_at=requested_at,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_no_active_job_when_none_exists(db: Database):
    assert await db.get_active_summary_refresh_job() is None


@pytest.mark.asyncio
async def test_finds_running_job(db: Database):
    await _insert_job(db, job_id="job-1", status="running", requested_at=datetime.now())

    active = await db.get_active_summary_refresh_job()

    assert active is not None
    assert active["id"] == "job-1"


@pytest.mark.asyncio
async def test_finds_queued_job(db: Database):
    await _insert_job(db, job_id="job-2", status="queued", requested_at=datetime.now())

    active = await db.get_active_summary_refresh_job()

    assert active is not None
    assert active["id"] == "job-2"


@pytest.mark.asyncio
async def test_ignores_finished_jobs(db: Database):
    await _insert_job(db, job_id="job-3", status="success", requested_at=datetime.now())
    await _insert_job(db, job_id="job-4", status="failed", requested_at=datetime.now())

    assert await db.get_active_summary_refresh_job() is None


@pytest.mark.asyncio
async def test_ignores_stale_orphaned_job():
    """Un worker que se cae a mitad de una corrida deja el job en 'running'
    para siempre -- sin este filtro, ningun /trigger/summary volveria a
    correr nunca mas."""

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

    old = datetime.now() - timedelta(hours=2)
    await _insert_job(database, job_id="orphaned", status="running", requested_at=old)

    active = await database.get_active_summary_refresh_job(stale_after_seconds=3600)

    assert active is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_returns_most_recent_active_job_when_several_exist(db: Database):
    now = datetime.now()
    await _insert_job(db, job_id="older", status="running", requested_at=now - timedelta(minutes=5))
    await _insert_job(db, job_id="newer", status="queued", requested_at=now)

    active = await db.get_active_summary_refresh_job()

    assert active["id"] == "newer"
