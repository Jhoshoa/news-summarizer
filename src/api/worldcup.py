from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import APIRouter, Header, HTTPException

from src.api.security import require_cron_key

router = APIRouter(prefix="/api/worldcup", tags=["worldcup"])


def create_worldcup_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    @router.get("/matches")
    async def get_worldcup_matches(match_date: date | None = None):
        app_instance = get_app_instance()
        return await app_instance.db.get_worldcup_matches(match_date)

    @router.post("/{match_id}/start")
    async def start_match(
        match_id: int,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        app_instance = get_app_instance()
        await require_cron_key(app_instance, x_api_key)
        result = await app_instance.db.start_match(match_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        return result

    @router.patch("/{match_id}/finish")
    async def finish_match(
        match_id: int,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        app_instance = get_app_instance()
        await require_cron_key(app_instance, x_api_key)
        try:
            result = await app_instance.db.finish_match(match_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        if result is None:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        return result

    @router.put("/{match_id}/score")
    async def update_score(
        match_id: int,
        home_score: int,
        away_score: int,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        app_instance = get_app_instance()
        await require_cron_key(app_instance, x_api_key)
        result = await app_instance.db.update_match_score(match_id, home_score, away_score)
        if result is None:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        return result

    return router
