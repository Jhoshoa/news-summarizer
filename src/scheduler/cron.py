from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from loguru import logger


class NewsScheduler:
    """Programa el envío de resúmenes automáticos."""

    def __init__(self, app, settings):
        self.app = app
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone=settings.schedule_timezone)
        logger.info(
            f"Scheduler inicializado para timezone={settings.schedule_timezone}"
        )

    def start(self):
        """Inicia el scheduler con los jobs configurados."""

        if self.settings.schedule_summary_morning:
            try:
                hour, minute = self.settings.schedule_summary_morning.split(":")
                self.scheduler.add_job(
                    self._send_morning_summary,
                    CronTrigger(hour=int(hour), minute=int(minute)),
                    id="morning_summary",
                    replace_existing=True,
                    name="Morning Summary",
                )
                logger.info(f"Job morning configurado para {hour}:{minute}")
            except Exception as e:
                logger.error(f"Error configurando morning job: {e}")

        if self.settings.schedule_summary_evening:
            try:
                hour, minute = self.settings.schedule_summary_evening.split(":")
                self.scheduler.add_job(
                    self._send_evening_summary,
                    CronTrigger(hour=int(hour), minute=int(minute)),
                    id="evening_summary",
                    replace_existing=True,
                    name="Evening Summary",
                )
                logger.info(f"Job evening configurado para {hour}:{minute}")
            except Exception as e:
                logger.error(f"Error configurando evening job: {e}")

        self.scheduler.start()
        logger.info("Scheduler iniciado")

    async def _send_morning_summary(self):
        """Envía el resumen de la mañana."""

        logger.info("Iniciando envío de resumen matutino...")

        try:
            await self.app.send_summaries("morning")
            logger.info("Resumen matutino enviado")
        except Exception as e:
            logger.error(f"Error enviando resumen matutino: {e}")

    async def _send_evening_summary(self):
        """Envía el resumen de la tarde."""

        logger.info("Iniciando envío de resumen vespertino...")

        try:
            await self.app.send_summaries("evening")
            logger.info("Resumen vespertino enviado")
        except Exception as e:
            logger.error(f"Error enviando resumen vespertino: {e}")

    def stop(self):
        """Detiene el scheduler."""

        self.scheduler.shutdown()
        logger.info("Scheduler detenido")

    def get_jobs(self):
        """Obtiene los jobs programados."""

        return self.scheduler.get_jobs()
