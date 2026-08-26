from collections.abc import Callable
from datetime import date as date_cls
from datetime import datetime
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.api.db_errors import call_db
from src.db.repository import DEFAULT_CATEGORIES

NewsView = Literal["resumenes", "recolectadas"]


class CategoryCount(BaseModel):
    slug: str
    label: str
    count: int


class CategoryCountsResponse(BaseModel):
    counts: list[CategoryCount]
    total: int
    date: date_cls
    requested_date: date_cls
    is_fallback: bool


def _today_for_app(app_instance: Any) -> date_cls:
    timezone_name = getattr(app_instance.settings, "schedule_timezone", "America/La_Paz")
    try:
        return datetime.now(ZoneInfo(timezone_name)).date()
    except ZoneInfoNotFoundError:
        return date_cls.today()


def create_news_categories_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/api/news", tags=["news"])

    @router.get("/category-counts", response_model=CategoryCountsResponse)
    async def get_category_counts(
        view: Annotated[
            NewsView,
            Query(description="'resumenes' cuenta briefs; 'recolectadas' cuenta articulos crudos."),
        ] = "resumenes",
        date: Annotated[
            date_cls | None,
            Query(description="Fecha en formato YYYY-MM-DD. Por defecto usa hoy."),
        ] = None,
        fallback_to_latest: Annotated[
            bool,
            Query(description="Si no hay datos para la fecha solicitada, cuenta la fecha anterior disponible."),
        ] = False,
    ):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        today = _today_for_app(app_instance)
        target_date = date or today
        if target_date > today:
            raise HTTPException(status_code=422, detail="La fecha no puede ser futura")

        result = await call_db(
            app_instance.db.get_category_counts(
                view=view,
                target_date=target_date,
                fallback_to_latest=fallback_to_latest,
            ),
            action="get_category_counts",
        )
        raw_counts: dict[str, int] = result["counts"]

        counts = [
            CategoryCount(slug=slug, label=label, count=raw_counts.get(slug, 0))
            for slug, label in DEFAULT_CATEGORIES.items()
            if raw_counts.get(slug, 0) > 0
        ]

        return CategoryCountsResponse(
            counts=counts,
            total=result["total"],
            date=result["date"],
            requested_date=result["requested_date"],
            is_fallback=result["is_fallback"],
        )

    return router
