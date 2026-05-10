from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query


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
        page: Annotated[int, Query(ge=1, description="Pagina solicitada.")] = 1,
        page_size: Annotated[
            int,
            Query(ge=1, le=100, description="Cantidad de articulos por pagina."),
        ] = 20,
    ):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        return await app_instance.db.list_articles(
            category=category,
            source=source,
            q=q,
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
