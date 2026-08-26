from __future__ import annotations

from collections.abc import Awaitable
from typing import TypeVar

import sentry_sdk
from fastapi import HTTPException
from loguru import logger

T = TypeVar("T")


async def call_db(coro: Awaitable[T], *, action: str) -> T:
    """Runs a DB call and turns an unexpected failure (e.g. a dropped
    connection to the database mid-request) into a clean 503 instead of a
    raw 500 -- still logged and reported to Sentry, just not leaked to the
    client as an unhandled OSError/DBAPIError.

    `app_instance.db is not None` only proves the DB was reachable at
    startup; it says nothing about whether *this* query will succeed, so
    every endpoint that awaits a DB call should route it through this
    instead of awaiting it directly.
    """

    try:
        return await coro
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error de base de datos en {action}: {e}")
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar con la base de datos. Intenta de nuevo en un momento.",
        ) from e
