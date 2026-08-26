from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.db_errors import call_db
from src.api.security import require_cron_key


class StoryCorrectionIn(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    corrected_by: str | None = Field(default=None, max_length=120)


def create_stories_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/api/stories", tags=["stories"])

    @router.get("")
    async def list_stories(
        category: str | None = None,
        min_sources: int = Query(default=1, ge=1, le=50),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        items, total = await call_db(
            app_instance.db.list_stories(
                category=category,
                min_sources=min_sources,
                page=page,
                page_size=page_size,
            ),
            action="list_stories",
        )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @router.get("/{story_id}")
    async def get_story(story_id: str):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        story = await call_db(app_instance.db.get_story(story_id), action="get_story")
        if story is None:
            raise HTTPException(status_code=404, detail="Historia no encontrada")
        return story

    @router.post("/{story_id}/corrections", status_code=201)
    async def add_story_correction(
        story_id: str,
        body: StoryCorrectionIn,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        """Registra una correccion (Fase 2.5). Accion administrativa: requiere
        la misma API key interna que /api/analytics — no hay panel editorial
        propio todavia (Fase 5)."""

        app_instance = get_app_instance()
        await require_cron_key(app_instance, x_api_key)
        if not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        correction = await call_db(
            app_instance.db.add_story_correction(
                story_id, reason=body.reason, corrected_by=body.corrected_by
            ),
            action="add_story_correction",
        )
        if correction is None:
            raise HTTPException(status_code=404, detail="Historia no encontrada")
        return correction

    @router.post("/{story_id}/unpublish", status_code=200)
    async def unpublish_story(
        story_id: str,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        app_instance = get_app_instance()
        await require_cron_key(app_instance, x_api_key)
        if not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        found = await call_db(
            app_instance.db.set_story_publication_status(story_id, unpublished=True),
            action="unpublish_story",
        )
        if not found:
            raise HTTPException(status_code=404, detail="Historia no encontrada")
        return {"id": story_id, "current_status": "unpublished"}

    @router.post("/{story_id}/republish", status_code=200)
    async def republish_story(
        story_id: str,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        app_instance = get_app_instance()
        await require_cron_key(app_instance, x_api_key)
        if not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        found = await call_db(
            app_instance.db.set_story_publication_status(story_id, unpublished=False),
            action="republish_story",
        )
        if not found:
            raise HTTPException(status_code=404, detail="Historia no encontrada")
        return {"id": story_id}

    return router
