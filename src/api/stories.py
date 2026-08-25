from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Query


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

        items, total = await app_instance.db.list_stories(
            category=category,
            min_sources=min_sources,
            page=page,
            page_size=page_size,
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

        story = await app_instance.db.get_story(story_id)
        if story is None:
            raise HTTPException(status_code=404, detail="Historia no encontrada")
        return story

    return router
