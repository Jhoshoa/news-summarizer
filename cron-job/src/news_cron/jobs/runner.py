from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, time, timedelta
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from news_cron.clients import BackendClient
from news_cron.clients.backend import BackendRequestError
from news_cron.config import CronSettings
from news_cron.utils import utc_now

LOGGER = logging.getLogger("news_summarizer_cron")


class RefreshJobRunner:
    def __init__(self, settings: CronSettings):
        self.settings = settings
        self.backend = BackendClient(settings)
        self._stop_event = asyncio.Event()

    async def close(self) -> None:
        await self.backend.close()

    def request_stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        LOGGER.info(
            "cron job started backend=%s run_once=%s",
            self.settings.backend_base_url,
            self.settings.run_once,
        )
        delivery_next = {
            window: self._next_delivery_run(scheduled_at)
            for window, scheduled_at in self.settings.delivery_windows().items()
        }
        for window, scheduled_at in delivery_next.items():
            LOGGER.info("delivery window scheduled window=%s next_run=%s", window, scheduled_at)

        economic_ok = await self._run_safely("economic_refresh", self.run_economic_refresh())
        summary_ok = await self._run_safely("summary_refresh", self.run_summary_refresh())

        if self.settings.run_once:
            if not economic_ok or not summary_ok:
                raise RuntimeError("RUN_ONCE refresh failed")
            LOGGER.info("RUN_ONCE enabled; cron job finished")
            return

        economic_next = utc_now() + timedelta(
            seconds=self.settings.economic_refresh_interval_seconds
        )
        summary_next = utc_now() + timedelta(
            seconds=self.settings.summary_refresh_interval_seconds
        )

        while not self._stop_event.is_set():
            now = utc_now()
            if now >= economic_next:
                await self._run_safely("economic_refresh", self.run_economic_refresh())
                economic_next = utc_now() + timedelta(
                    seconds=self.settings.economic_refresh_interval_seconds
                )
            if now >= summary_next:
                await self._run_safely("summary_refresh", self.run_summary_refresh())
                summary_next = utc_now() + timedelta(
                    seconds=self.settings.summary_refresh_interval_seconds
                )
            for window, due_at in list(delivery_next.items()):
                if now >= due_at:
                    await self._run_safely(
                        f"delivery_{window}",
                        self.run_delivery_window(window),
                    )
                    delivery_next[window] = self._next_delivery_run(
                        self.settings.delivery_windows()[window]
                    )
                    LOGGER.info(
                        "delivery window rescheduled window=%s next_run=%s",
                        window,
                        delivery_next[window],
                    )

            next_waits = [
                max((economic_next - utc_now()).total_seconds(), 1),
                max((summary_next - utc_now()).total_seconds(), 1),
                60,
            ]
            next_waits.extend(
                max((due_at - utc_now()).total_seconds(), 1)
                for due_at in delivery_next.values()
            )
            sleep_for = min(next_waits)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_for)
            except TimeoutError:
                continue

    async def run_economic_refresh(self) -> None:
        payload = await self.backend.post_json(
            "/api/economic-indicators/refresh",
            timeout_seconds=self.settings.economic_request_timeout_seconds,
        )
        LOGGER.info(
            "economic refresh ok collected=%s inserted=%s unchanged=%s skipped=%s",
            payload.get("collected"),
            payload.get("inserted"),
            payload.get("unchanged"),
            payload.get("skipped"),
        )

    async def run_summary_refresh(self) -> None:
        query = urlencode({"time_of_day": self.settings.summary_time_of_day, "refresh": "true"})
        payload = await self.backend.post_json(
            f"{self.settings.summary_trigger_path}?{query}",
            timeout_seconds=self.settings.summary_request_timeout_seconds,
        )
        result = payload.get("result") or {}
        LOGGER.info(
            "summary refresh ok collected=%s processed=%s summaries=%s sent=%s",
            result.get("collected"),
            result.get("processed"),
            result.get("summaries"),
            result.get("sent"),
        )

    async def run_delivery_window(self, time_of_day: str) -> None:
        query = urlencode({"time_of_day": time_of_day})
        payload = await self.backend.post_json(
            f"{self.settings.delivery_trigger_path}?{query}",
            timeout_seconds=self.settings.delivery_request_timeout_seconds,
        )
        result = payload.get("result") or {}
        LOGGER.info(
            "summary delivery ok window=%s summaries=%s sent=%s",
            time_of_day,
            result.get("summaries"),
            result.get("sent"),
        )

    def _next_delivery_run(self, scheduled_at: str, *, after: datetime | None = None) -> datetime:
        zone = ZoneInfo(self.settings.schedule_timezone)
        now = (after or utc_now()).astimezone(zone)
        hour, minute = (int(part) for part in scheduled_at.split(":", maxsplit=1))
        candidate = datetime.combine(now.date(), time(hour, minute), tzinfo=zone)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate.astimezone(UTC)

    async def _run_safely(self, name: str, task: Any) -> bool:
        try:
            await task
            return True
        except BackendRequestError as exc:
            LOGGER.error("job failed name=%s error=%s", name, exc)
            return False
        except Exception:
            LOGGER.exception("job failed unexpectedly name=%s", name)
            return False
