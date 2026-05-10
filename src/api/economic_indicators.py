from collections.abc import Callable
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from src.collectors.economic_indicators import EconomicIndicatorCollector
from src.db import EconomicIndicatorRepository


def create_economic_indicators_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/api/economic-indicators", tags=["economic-indicators"])

    @router.get("")
    async def get_latest_economic_indicators(
        target_date: Annotated[
            date | None,
            Query(
                alias="date",
                description=(
                    "Fecha en formato YYYY-MM-DD. Si se omite, devuelve los últimos "
                    "valores conocidos."
                ),
            ),
        ] = None,
    ):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        repository = EconomicIndicatorRepository(app_instance.db.session_maker)
        indicators = await repository.get_latest_values(target_date=target_date)
        return {
            "count": len(indicators),
            "date": target_date,
            "items": indicators,
        }

    @router.post("/refresh")
    async def refresh_economic_indicators():
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        collector = EconomicIndicatorCollector(timeout=app_instance.settings.scraper_timeout)
        try:
            indicators = await collector.fetch_all()
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"No se pudieron obtener indicadores economicos: {exc}",
            ) from exc

        repository = EconomicIndicatorRepository(app_instance.db.session_maker)
        stats = await repository.save_values(indicators)
        latest = await repository.get_latest_values()
        return {
            "status": "success",
            "collected": len(indicators),
            "inserted": stats["inserted"],
            "unchanged": stats["unchanged"],
            "skipped": stats["skipped"],
            "items": latest,
        }

    return router
