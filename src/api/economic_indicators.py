from collections.abc import Callable
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query
from loguru import logger

from src.api.security import require_cron_key
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
    async def refresh_economic_indicators(
        x_api_key: Annotated[
            str | None,
            Header(alias="X-API-Key", description="Clave privada para endpoints internos."),
        ] = None,
    ):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")
        await require_cron_key(app_instance, x_api_key)

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
        logger.info(
            "Economic indicators refresh completed: "
            f"collected={len(indicators)} inserted={stats['inserted']} "
            f"unchanged={stats['unchanged']} skipped={stats['skipped']}"
        )
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
