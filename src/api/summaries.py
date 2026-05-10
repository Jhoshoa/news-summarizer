from collections.abc import Callable
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query


def create_summaries_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/api/summaries", tags=["summaries"])

    @router.get("")
    async def list_summaries(
        category: Annotated[
            str | None,
            Query(description="Categoria normalizada, por ejemplo economia o politica."),
        ] = None,
        summary_date: Annotated[
            date | None,
            Query(
                alias="date",
                description="Fecha del resumen en formato YYYY-MM-DD. Si se omite, usa hoy.",
            ),
        ] = None,
        article_id: Annotated[
            int | None,
            Query(description="Filtra summaries asociados a un articulo especifico."),
        ] = None,
        page: Annotated[int, Query(ge=1, description="Pagina solicitada.")] = 1,
        page_size: Annotated[
            int,
            Query(ge=1, le=100, description="Cantidad de summaries por pagina."),
        ] = 20,
    ):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        return await app_instance.db.list_summaries(
            category=category,
            summary_date=summary_date,
            article_id=article_id,
            page=page,
            page_size=page_size,
        )

    @router.get("/{summary_id}")
    async def get_summary(summary_id: int):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        summary = await app_instance.db.get_summary_by_id(summary_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Resumen no encontrado")

        return summary

    return router
