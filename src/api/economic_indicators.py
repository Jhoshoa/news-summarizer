from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query
from loguru import logger

from src.api.db_errors import call_db
from src.api.security import require_cron_key
from src.collectors.economic_indicators import TZ_BOLIVIA, EconomicIndicatorCollector
from src.db import EconomicIndicatorRepository

DEFAULT_HISTORY_CODES = [
    "bcb_tipo_de_cambio_oficial",
    "binance_p2p_usdt_bob_buy",
    "binance_p2p_usdt_bob_sell",
]
MAX_HISTORY_DAYS = 365


def create_economic_indicators_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/api/economic-indicators", tags=["economic-indicators"])

    @router.get("/history")
    async def get_economic_indicators_history(
        codes: Annotated[
            str | None,
            Query(
                description=(
                    "Codigos de indicador separados por coma. Por defecto: dolar "
                    "oficial del BCB y compra/venta de Binance P2P."
                ),
            ),
        ] = None,
        days: Annotated[
            int,
            Query(ge=1, le=MAX_HISTORY_DAYS, description="Dias de historial hacia atras."),
        ] = 120,
    ):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        indicator_codes = (
            [c.strip() for c in codes.split(",") if c.strip()] if codes else DEFAULT_HISTORY_CODES
        )
        since = datetime.now(TZ_BOLIVIA).replace(tzinfo=None) - timedelta(days=days)

        repository = EconomicIndicatorRepository(app_instance.db.session_maker)
        history = await call_db(
            repository.get_history(indicator_codes, since), action="get_history"
        )
        return {"since": since, "days": days, "series": history}

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
        indicators = await call_db(
            repository.get_latest_values(target_date=target_date), action="get_latest_values"
        )
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
        stats = await call_db(repository.save_values(indicators), action="save_values")
        logger.info(
            "Economic indicators refresh completed: "
            f"collected={len(indicators)} inserted={stats['inserted']} "
            f"unchanged={stats['unchanged']} skipped={stats['skipped']}"
        )
        latest = await call_db(repository.get_latest_values(), action="get_latest_values")

        price_alert = getattr(app_instance, "price_alert", None)
        if price_alert:
            try:
                await price_alert.check_and_notify(latest)
            except Exception as exc:
                logger.error(f"Error chequeando alertas de precio: {exc}")

        return {
            "status": "success",
            "collected": len(indicators),
            "inserted": stats["inserted"],
            "unchanged": stats["unchanged"],
            "skipped": stats["skipped"],
            "items": latest,
        }

    return router
