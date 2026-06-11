from __future__ import annotations

import asyncio
import logging
import os
import signal
from contextlib import suppress

from news_cron.config import CronSettings
from news_cron.jobs import RefreshJobRunner

LOGGER = logging.getLogger("news_summarizer_cron")


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if not os.getenv("LOG_HTTP_DEBUG"):
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)


async def async_main() -> int:
    configure_logging()
    try:
        settings = CronSettings.from_env()
    except ValueError as exc:
        LOGGER.error("configuration error: %s", exc)
        return 2

    runner = RefreshJobRunner(settings)
    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        signum = getattr(signal, signame, None)
        if signum is None:
            continue
        with suppress(NotImplementedError):
            loop.add_signal_handler(signum, runner.request_stop)

    try:
        await runner.run()
    except Exception:
        LOGGER.exception("cron job failed")
        return 1
    finally:
        await runner.close()

    return 0


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
