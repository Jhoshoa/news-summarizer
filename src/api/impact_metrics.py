from collections.abc import Callable
from datetime import date as date_cls
from datetime import datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query


def _today_for_app(app_instance: Any) -> date_cls:
    timezone_name = getattr(app_instance.settings, "schedule_timezone", "America/La_Paz")
    try:
        return datetime.now(ZoneInfo(timezone_name)).date()
    except ZoneInfoNotFoundError:
        return date_cls.today()


def create_impact_metrics_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/api/impact-metrics", tags=["impact"])

    @router.get("")
    async def get_impact_metrics(
        metrics_date: Annotated[
            date_cls | None,
            Query(
                alias="date",
                description="Fecha de metricas en formato YYYY-MM-DD. Si se omite, usa hoy.",
            ),
        ] = None,
        fallback_to_latest: Annotated[
            bool,
            Query(description="Si no hay metricas para la fecha solicitada, usa la fecha anterior disponible."),
        ] = True,
    ):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        today = _today_for_app(app_instance)
        requested_date = metrics_date or today
        if requested_date > today:
            raise HTTPException(status_code=422, detail="La fecha no puede ser futura")

        return await app_instance.db.get_impact_metrics(
            requested_date,
            fallback_to_latest=fallback_to_latest,
        )

    return router
