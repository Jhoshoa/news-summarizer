from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from news_cron.config import CronSettings
from news_cron.utils import utc_now

LOGGER = logging.getLogger("news_summarizer_cron")


class BackendClient:
    def __init__(self, settings: CronSettings):
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=settings.backend_base_url,
            headers={"X-API-Key": settings.api_auth_key},
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def post_json(self, path: str, *, timeout_seconds: float) -> dict[str, Any]:
        last_error: Exception | None = None
        attempts = self.settings.request_retries + 1

        for attempt in range(1, attempts + 1):
            started_at = utc_now()
            try:
                LOGGER.info("request start path=%s attempt=%s/%s", path, attempt, attempts)
                response = await self.client.post(
                    path,
                    timeout=httpx.Timeout(timeout_seconds),
                )
                response.raise_for_status()
                elapsed = (utc_now() - started_at).total_seconds()
                LOGGER.info(
                    "request finished path=%s status=%s elapsed=%.2fs",
                    path,
                    response.status_code,
                    elapsed,
                )
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                LOGGER.warning(
                    "request failed path=%s attempt=%s/%s error=%s",
                    path,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    await asyncio.sleep(min(2**attempt, 30))

        raise RuntimeError(f"request failed after {attempts} attempts: {path}") from last_error
