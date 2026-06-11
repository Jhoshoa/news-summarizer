from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger


class NewsScheduler:
    """Programa el envio automatico de briefs."""

    def __init__(self, app, settings):
        self.app = app
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone=settings.schedule_timezone)
        logger.info(f"Scheduler inicializado para timezone={settings.schedule_timezone}")

    def start(self):
        """Inicia el scheduler con los jobs configurados."""

        self._add_summary_job(
            schedule_value=self.settings.schedule_summary_morning,
            time_of_day="morning",
            job_id="morning_summary",
            name="Morning Summary",
        )
        self._add_summary_job(
            schedule_value=self.settings.schedule_summary_afternoon,
            time_of_day="afternoon",
            job_id="afternoon_summary",
            name="Afternoon Summary",
        )
        self._add_summary_job(
            schedule_value=self.settings.schedule_summary_night,
            time_of_day="night",
            job_id="night_summary",
            name="Night Summary",
        )
        self._add_summary_job(
            schedule_value=self.settings.schedule_summary_evening,
            time_of_day="evening",
            job_id="evening_summary",
            name="Evening Summary Legacy",
        )

        self.scheduler.start()
        logger.info("Scheduler iniciado")

    def _add_summary_job(
        self,
        *,
        schedule_value: str | None,
        time_of_day: str,
        job_id: str,
        name: str,
    ) -> None:
        if not schedule_value:
            return

        try:
            hour, minute = schedule_value.split(":")
            self.scheduler.add_job(
                self._send_summary_for_window,
                CronTrigger(hour=int(hour), minute=int(minute)),
                args=[time_of_day],
                id=job_id,
                replace_existing=True,
                name=name,
            )
            logger.info(f"Job {time_of_day} configurado para {hour}:{minute}")
        except Exception as e:
            logger.error(f"Error configurando job {time_of_day}: {e}")

    async def _send_morning_summary(self):
        """Envia el resumen de la manana."""

        await self._send_summary_for_window("morning")

    async def _send_afternoon_summary(self):
        """Envia el resumen de la tarde."""

        await self._send_summary_for_window("afternoon")

    async def _send_night_summary(self):
        """Envia el resumen de la noche."""

        await self._send_summary_for_window("night")

    async def _send_evening_summary(self):
        """Envia el resumen vespertino legacy."""

        await self._send_summary_for_window("evening")

    async def _send_summary_for_window(self, time_of_day: str):
        """Envia resumen para una ventana configurada."""

        logger.info(f"Iniciando envio de resumen: {time_of_day}")
        try:
            await self.app.deliver_cached_summaries(time_of_day)
            logger.info(f"Resumen {time_of_day} enviado")
        except Exception as e:
            logger.error(f"Error enviando resumen {time_of_day}: {e}")

    def stop(self):
        """Detiene el scheduler."""

        self.scheduler.shutdown()
        logger.info("Scheduler detenido")

    def get_jobs(self):
        """Obtiene los jobs programados."""

        return self.scheduler.get_jobs()
