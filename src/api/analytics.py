from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header
from loguru import logger
from pydantic import BaseModel, Field

from src.api.db_errors import call_db
from src.api.security import require_cron_key

TZ_BOLIVIA = ZoneInfo("America/La_Paz")

ALLOWED_EVENT_NAMES = {
    "user_registered",
    "onboarding_completed",
    "brief_opened",
    "story_opened",
    "source_clicked",
    "category_followed",
    "entity_followed",
    "story_saved",
    "story_shared",
    "alert_created",
    "feedback_submitted",
    "report_generated",
}


class AnalyticsEventIn(BaseModel):
    event_name: str = Field(min_length=1, max_length=60)
    user_id: int | None = None
    session_id: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=10)
    department: str | None = Field(default=None, max_length=80)
    category: str | None = Field(default=None, max_length=60)
    story_id: str | None = Field(default=None, max_length=64)
    source_id: str | None = Field(default=None, max_length=120)
    device: str | None = Field(default=None, max_length=20)
    metadata: dict[str, Any] | None = None


class AnalyticsEventsRequest(BaseModel):
    events: list[AnalyticsEventIn] = Field(min_length=1, max_length=50)


class AnalyticsEventsResponse(BaseModel):
    accepted: int
    skipped: int


class AnalyticsSummaryResponse(BaseModel):
    since: datetime
    event_counts: dict[str, int]
    unique_sessions: int
    unique_users: int


class PipelineTotals(BaseModel):
    since: datetime
    total_runs: int
    failed_runs: int
    raw_collected: int
    usable: int
    quality_dropped: int
    deduplicated: int
    duplicate_dropped: int
    summary_candidates: int
    summaries: int
    ai_dedup_avoided: int


class ReturningSessions(BaseModel):
    cohort_days: int
    current_sessions: int
    returning_sessions: int
    returning_rate: float


class MetricsDashboardResponse(BaseModel):
    product: AnalyticsSummaryResponse
    pipeline: PipelineTotals
    returning: ReturningSessions
    active_subscribers: int


def _resolve_since(days: int) -> datetime:
    return datetime.now(TZ_BOLIVIA).replace(tzinfo=None) - timedelta(days=max(1, min(days, 90)))


def create_analytics_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/api/analytics", tags=["analytics"])

    @router.post("/events", response_model=AnalyticsEventsResponse, status_code=202)
    async def ingest_events(request: AnalyticsEventsRequest):
        # Telemetria: eventos con nombre desconocido se descartan en vez de
        # rechazar el batch completo, para no perder el resto por un cliente
        # desactualizado.
        valid_events = [
            event for event in request.events if event.event_name in ALLOWED_EVENT_NAMES
        ]
        skipped = len(request.events) - len(valid_events)

        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            logger.warning(
                f"Analytics events descartados, DB no disponible: {len(valid_events)} eventos"
            )
            return AnalyticsEventsResponse(accepted=0, skipped=len(request.events))

        try:
            accepted = await app_instance.db.record_events(
                [event.model_dump() for event in valid_events]
            )
        except Exception as e:
            logger.error(f"Error guardando analytics events: {e}")
            return AnalyticsEventsResponse(accepted=0, skipped=len(request.events))

        return AnalyticsEventsResponse(accepted=accepted, skipped=skipped)

    @router.get("/summary", response_model=AnalyticsSummaryResponse)
    async def get_summary(
        days: int = 7,
        x_api_key: Annotated[
            str | None,
            Header(alias="X-API-Key", description="Clave privada para endpoints internos."),
        ] = None,
    ):
        app_instance = get_app_instance()
        await require_cron_key(app_instance, x_api_key)

        since = _resolve_since(days)
        if not app_instance.db:
            return AnalyticsSummaryResponse(
                since=since, event_counts={}, unique_sessions=0, unique_users=0
            )
        summary = await call_db(
            app_instance.db.get_analytics_summary(since), action="get_analytics_summary"
        )
        return AnalyticsSummaryResponse(**summary)

    @router.get("/dashboard", response_model=MetricsDashboardResponse)
    async def get_dashboard(
        days: int = 7,
        x_api_key: Annotated[
            str | None,
            Header(alias="X-API-Key", description="Clave privada para endpoints internos."),
        ] = None,
    ):
        """Panel interno minimo (roadmap YC Fase 0.2): uso de producto + eficiencia
        del pipeline en la misma vista. Complementa /api/impact-metrics (Green Tech),
        no lo reemplaza: ver documentation/yc-roadmap/alineacion-green-tech.md."""

        app_instance = get_app_instance()
        await require_cron_key(app_instance, x_api_key)

        since = _resolve_since(days)
        if not app_instance.db:
            return MetricsDashboardResponse(
                product=AnalyticsSummaryResponse(
                    since=since, event_counts={}, unique_sessions=0, unique_users=0
                ),
                pipeline=PipelineTotals(
                    since=since,
                    total_runs=0,
                    failed_runs=0,
                    raw_collected=0,
                    usable=0,
                    quality_dropped=0,
                    deduplicated=0,
                    duplicate_dropped=0,
                    summary_candidates=0,
                    summaries=0,
                    ai_dedup_avoided=0,
                ),
                returning=ReturningSessions(
                    cohort_days=days, current_sessions=0, returning_sessions=0, returning_rate=0.0
                ),
                active_subscribers=0,
            )

        product = await call_db(
            app_instance.db.get_analytics_summary(since), action="get_analytics_summary"
        )
        pipeline = await call_db(
            app_instance.db.get_pipeline_totals(since), action="get_pipeline_totals"
        )
        returning = await call_db(
            app_instance.db.get_returning_session_rate(since, cohort_days=days),
            action="get_returning_session_rate",
        )
        active_subscribers = await call_db(
            app_instance.db.get_subscription_count(), action="get_subscription_count"
        )

        return MetricsDashboardResponse(
            product=AnalyticsSummaryResponse(**product),
            pipeline=PipelineTotals(**pipeline),
            returning=ReturningSessions(**returning),
            active_subscribers=active_subscribers,
        )

    return router
