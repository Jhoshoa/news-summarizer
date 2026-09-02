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
            hour: self._next_delivery_run(hour) for hour in self.settings.delivery_hours
        }
        for hour, scheduled_at in delivery_next.items():
            LOGGER.info("delivery window scheduled hour=%s next_run=%s", hour, scheduled_at)

        if self.settings.summary_refresh_hours:
            LOGGER.info("summary refresh hours=%s", self.settings.summary_refresh_hours)
        else:
            LOGGER.info(
                "summary refresh interval=%s seconds",
                self.settings.summary_refresh_interval_seconds,
            )

        await self._run_safely("economic_refresh", self.run_economic_refresh())

        if self.settings.run_once:
            LOGGER.info("RUN_ONCE enabled; cron job finished")
            return

        economic_next = utc_now() + timedelta(
            seconds=self.settings.economic_refresh_interval_seconds
        )
        summary_next = (
            self._next_summary_run()
            if self.settings.summary_refresh_hours
            else utc_now() + timedelta(seconds=self.settings.summary_refresh_interval_seconds)
        )
        LOGGER.info("summary refresh scheduled next_run=%s", summary_next)

        while not self._stop_event.is_set():
            now = utc_now()
            if now >= economic_next:
                await self._run_safely("economic_refresh", self.run_economic_refresh())
                economic_next = utc_now() + timedelta(
                    seconds=self.settings.economic_refresh_interval_seconds
                )

            if now >= summary_next:
                if self.settings.summary_refresh_hours:
                    await self._run_safely("summary_refresh", self.run_summary_refresh())
                    summary_next = self._next_summary_run(after=summary_next)
                else:
                    await self._run_safely("summary_refresh", self.run_summary_refresh())
                    summary_next = utc_now() + timedelta(
                        seconds=self.settings.summary_refresh_interval_seconds
                    )
                LOGGER.info("summary refresh rescheduled next_run=%s", summary_next)

            for hour, due_at in list(delivery_next.items()):
                if now >= due_at:
                    await self._run_safely(
                        f"delivery_{hour:02d}",
                        self.run_delivery_window(hour),
                    )
                    delivery_next[hour] = self._next_delivery_run(hour, after=due_at)
                    LOGGER.info(
                        "delivery window rescheduled hour=%s next_run=%s",
                        hour,
                        delivery_next[hour],
                    )

            waits = [
                max((economic_next - utc_now()).total_seconds(), 1),
                60,
            ]
            waits.append(max((summary_next - utc_now()).total_seconds(), 1))
            waits.extend(
                max((due_at - utc_now()).total_seconds(), 1)
                for due_at in delivery_next.values()
            )
            sleep_for = min(waits)
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
        """Lanza el refresh de resumenes en modo asincrono y sondea su estado.

        Antes esto era un solo POST bloqueante con un timeout fijo
        (SUMMARY_REQUEST_TIMEOUT_SECONDS): si el pipeline tardaba mas que
        eso -- algo que pasa seguido, se vio en vivo una corrida de 573s
        contra un timeout de 300s -- httpx lo marcaba como fallido y
        REQUEST_RETRIES volvia a lanzar el mismo trigger encima del que
        seguia corriendo en el backend, sin que nada lo cancelara. Con
        async_mode=true el backend devuelve un job_id de inmediato (o el
        job ya en curso, gracias al candado de concurrencia agregado en
        main.py) y este metodo solo consulta su estado hasta que termine,
        sin volver a disparar el pipeline.
        """

        query = urlencode(
            {
                "time_of_day": self.settings.summary_time_of_day,
                "refresh": "true",
                "async_mode": "true",
            }
        )
        payload = await self.backend.post_json(
            f"{self.settings.summary_trigger_path}?{query}",
            timeout_seconds=self.settings.summary_request_timeout_seconds,
        )
        status_url = payload.get("status_url")
        job = payload.get("job") or {}
        if not status_url:
            LOGGER.warning("summary refresh: respuesta sin status_url, payload=%s", payload)
            return

        result = await self._poll_summary_job(status_url, initial_status=job.get("status"))
        LOGGER.info(
            "summary refresh ok collected=%s processed=%s summaries=%s sent=%s",
            result.get("collected"),
            result.get("processed"),
            result.get("summaries"),
            result.get("sent"),
        )

    async def _poll_summary_job(self, status_url: str, *, initial_status: str | None) -> dict:
        deadline = utc_now() + timedelta(seconds=self.settings.summary_job_max_wait_seconds)
        status = initial_status
        job: dict[str, Any] = {}

        while status not in ("success", "failed"):
            if utc_now() >= deadline:
                raise BackendRequestError(
                    status_url, 1, TimeoutError("summary job did not finish before max wait")
                )
            await asyncio.sleep(self.settings.summary_poll_interval_seconds)
            payload = await self.backend.get_json(
                status_url,
                timeout_seconds=self.settings.summary_request_timeout_seconds,
            )
            job = payload.get("job") or {}
            status = job.get("status")

        if not job:
            # initial_status ya era terminal (job ya habia terminado cuando lo
            # devolvio el POST inicial) -- traer el job completo con su result.
            payload = await self.backend.get_json(
                status_url,
                timeout_seconds=self.settings.summary_request_timeout_seconds,
            )
            job = payload.get("job") or {}

        if status == "failed":
            raise BackendRequestError(status_url, 1, RuntimeError(job.get("error_message") or "job failed"))
        return job.get("result") or {}

    async def run_delivery_window(self, hour: int) -> None:
        query = urlencode({"hour": hour})
        payload = await self.backend.post_json(
            f"{self.settings.delivery_trigger_path}?{query}",
            timeout_seconds=self.settings.delivery_request_timeout_seconds,
        )
        result = payload.get("result") or {}
        LOGGER.info(
            "summary delivery ok hour=%s summaries=%s sent=%s",
            hour,
            result.get("summaries"),
            result.get("sent"),
        )

    def _next_delivery_run(self, hour: int, *, after: datetime | None = None) -> datetime:
        zone = ZoneInfo(self.settings.schedule_timezone)
        now = (after or utc_now()).astimezone(zone)
        candidate = datetime.combine(now.date(), time(hour, 0), tzinfo=zone)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate.astimezone(UTC)

    def _next_summary_run(self, *, after: datetime | None = None) -> datetime:
        zone = ZoneInfo(self.settings.schedule_timezone)
        now = (after or utc_now()).astimezone(zone)
        for hour in self.settings.summary_refresh_hours or []:
            candidate = datetime.combine(now.date(), time(hour, 0), tzinfo=zone)
            if candidate > now:
                return candidate.astimezone(UTC)

        first_hour = (self.settings.summary_refresh_hours or [0])[0]
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, time(first_hour, 0), tzinfo=zone).astimezone(UTC)

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
