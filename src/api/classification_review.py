from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.api.db_errors import call_db as _call_db
from src.api.security import require_cron_key
from src.db.repository import DEFAULT_CATEGORIES

# Ventana por defecto: la revision se dispara ~30 min despues de una corrida
# de resumen (ver cron), pero una corrida puede tardar bastante -- una
# ventana mas ancha que "los ultimos 30 min" evita perder articulos si la
# corrida se atraso o si la revision se disparo con algo de retraso.
DEFAULT_REVIEW_WINDOW_MINUTES = 180
MAX_REVIEW_LIMIT = 100


class ReviewCandidate(BaseModel):
    id: int
    title: str
    description: str | None = None
    content: str | None = None
    url: str | None = None
    source: str | None = None
    category: str
    published_at: Any | None = None
    collected_at: Any | None = None
    category_method: str | None = None
    category_reason: str | None = None
    category_confidence: float | None = None
    category_scores: dict[str, float] | None = None
    category_llm_error: str | None = None


class ReviewQueueResponse(BaseModel):
    since_minutes: int
    count: int
    items: list[ReviewCandidate]


class CorrectionRequest(BaseModel):
    article_id: int
    category: str
    reason: str = Field(min_length=1, max_length=2000)
    corrected_by: str = "claude_scheduled_review"

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in DEFAULT_CATEGORIES:
            raise ValueError(f"Categoria desconocida: {value}")
        return normalized


class CorrectionResponse(BaseModel):
    status: str
    article_id: int
    previous_category: str | None = None
    category: str
    message: str


def _candidate_from_article(article: dict) -> ReviewCandidate:
    raw_payload = article.get("raw_payload") or {}
    return ReviewCandidate(
        id=article["id"],
        title=article.get("title") or "",
        description=article.get("description"),
        content=article.get("content"),
        url=article.get("url"),
        source=article.get("source"),
        category=article.get("category") or "general",
        published_at=article.get("published_at"),
        collected_at=article.get("collected_at"),
        category_method=raw_payload.get("category_method"),
        category_reason=raw_payload.get("category_reason"),
        category_confidence=raw_payload.get("category_confidence"),
        category_scores=raw_payload.get("category_scores"),
        category_llm_error=raw_payload.get("category_llm_error"),
    )


def create_classification_review_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    """Endpoints internos para que una revision externa (agente programado)
    encuentre y corrija articulos cuya categoria el clasificador ya marco
    como dudosa -- no reemplaza al clasificador, solo le da a un revisor con
    criterio (humano o agente) una lista acotada para mirar, en vez de tener
    que auditar toda la corrida.

    Protegidos con la misma API key que /trigger/* (X-API-Key /
    API_AUTH_KEY) -- no estan pensados para el frontend publico."""

    router = APIRouter(prefix="/admin/classification", tags=["classification-review"])

    @router.get("/review-queue", response_model=ReviewQueueResponse)
    async def get_review_queue(
        since_minutes: int = DEFAULT_REVIEW_WINDOW_MINUTES,
        limit: int = 50,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        app_instance = get_app_instance()
        if not app_instance:
            raise HTTPException(status_code=500, detail="App no inicializada")
        await require_cron_key(app_instance, x_api_key)

        if not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        since_minutes = max(1, min(since_minutes, 24 * 60))
        limit = max(1, min(limit, MAX_REVIEW_LIMIT))

        articles = await _call_db(
            app_instance.db.get_articles_needing_category_review(since_minutes, limit=limit),
            action="get_articles_needing_category_review",
        )

        return ReviewQueueResponse(
            since_minutes=since_minutes,
            count=len(articles),
            items=[_candidate_from_article(a) for a in articles],
        )

    @router.post("/correct", response_model=CorrectionResponse)
    async def correct_category(
        request: CorrectionRequest,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        app_instance = get_app_instance()
        if not app_instance:
            raise HTTPException(status_code=500, detail="App no inicializada")
        await require_cron_key(app_instance, x_api_key)

        if not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        before = await _call_db(
            app_instance.db.get_article_by_id(request.article_id),
            action="get_article_by_id",
        )
        if not before:
            raise HTTPException(status_code=404, detail="Articulo no encontrado")
        previous_category = before.get("category")

        # `request.category` ya paso por CorrectionRequest.validate_category
        # (solo acepta valores de DEFAULT_CATEGORIES), asi que el ValueError
        # que correct_article_category podria levantar por categoria
        # desconocida es inalcanzable por esta ruta -- se deja la validacion
        # ahi igual porque el metodo del repositorio no es exclusivo de este
        # endpoint.
        updated = await _call_db(
            app_instance.db.correct_article_category(
                request.article_id,
                request.category,
                reason=request.reason,
                corrected_by=request.corrected_by,
            ),
            action="correct_article_category",
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Articulo no encontrado")

        return CorrectionResponse(
            status="corrected",
            article_id=request.article_id,
            previous_category=previous_category,
            category=request.category,
            message=f"Categoria corregida de '{previous_category}' a '{request.category}'.",
        )

    return router
