from __future__ import annotations

import secrets
from typing import Any

from fastapi import Header, HTTPException, status


async def require_cron_key(
    app_instance: Any,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    settings = getattr(app_instance, "settings", None)
    expected_key = getattr(settings, "api_auth_key", None)

    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_AUTH_KEY no configurado",
        )

    if not x_api_key or not secrets.compare_digest(x_api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key invalida",
        )
