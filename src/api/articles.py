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


def create_articles_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/api/articles", tags=["articles"])

    @router.get("")
    async def list_articles(
        category: Annotated[
            str | None,
            Query(description="Categoria normalizada, por ejemplo economia o politica."),
        ] = None,
        source: Annotated[
            str | None,
            Query(description="Nombre de la fuente, por ejemplo RedUno o Unitel."),
        ] = None,
        q: Annotated[
            str | None,
            Query(description="Texto a buscar en titulo, descripcion o contenido."),
        ] = None,
        date: Annotated[
            date_cls | None,
            Query(description="Fecha de publicacion en formato YYYY-MM-DD. Por defecto usa hoy."),
        ] = None,
        fallback_to_latest: Annotated[
            bool,
            Query(description="Si no hay datos para la fecha solicitada, devuelve la fecha anterior disponible."),
        ] = False,
        page: Annotated[int, Query(ge=1, description="Pagina solicitada.")] = 1,
        page_size: Annotated[
            int,
            Query(ge=1, le=100, description="Cantidad de articulos por pagina."),
        ] = 20,
    ):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        today = _today_for_app(app_instance)
        article_date = date or today
        if article_date > today:
            raise HTTPException(status_code=422, detail="La fecha no puede ser futura")

        return await app_instance.db.list_articles(
            category=category,
            source=source,
            q=q,
            article_date=article_date,
            fallback_to_latest=fallback_to_latest,
            page=page,
            page_size=page_size,
        )

    @router.get("/{article_id}")
    async def get_article(article_id: int):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        article = await app_instance.db.get_article_by_id(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Articulo no encontrado")

        return article

    return router
