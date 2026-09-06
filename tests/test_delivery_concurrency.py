"""Tests for bounded concurrency in subscriber delivery.

Before this, `_deliver_summaries` sent to subscribers one at a time -- each
one a real network round-trip (Meta Graph API, Telegram Bot API, or a
blocking SMTP call via asyncio.to_thread). Same category of fix already
applied to the scraper (see tests/test_scraper_concurrency.py): a semaphore
now caps how many deliveries are in flight at once, without changing what
gets counted as sent/failed or how per-subscriber failures are isolated.
"""

import asyncio
from types import SimpleNamespace

import pytest

from src.main import NewsSummarizerApp


def _settings(**overrides):
    base = dict(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
        delivery_concurrency=3,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _subscriber(idx: int, channel: str = "whatsapp") -> SimpleNamespace:
    return SimpleNamespace(
        channel=channel,
        phone=f"+59170000{idx}" if channel == "whatsapp" else None,
        telegram_id=f"tg{idx}" if channel == "telegram" else None,
        email=f"user{idx}@example.com" if channel == "email" else None,
        categories=["politica"],
        preferred_hour=None,
        frequency="diario",
    )


class SubscriberDatabase:
    def __init__(self, subscribers):
        self.subscribers = subscribers

    async def get_active_subscribers(self):
        return self.subscribers


def _summaries():
    return [{"title": "Titulo", "summary": "Resumen", "category": "politica"}]


@pytest.mark.asyncio
async def test_deliver_summaries_never_exceeds_the_delivery_concurrency_limit():
    subscribers = [_subscriber(i) for i in range(9)]
    app = NewsSummarizerApp(_settings(delivery_concurrency=3))
    app.db = SubscriberDatabase(subscribers)

    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    class SlowWhatsApp:
        async def send_message(self, to, message):
            nonlocal in_flight, max_in_flight
            async with lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.05)
            async with lock:
                in_flight -= 1
            return True

    app.whatsapp = SlowWhatsApp()

    sent_count, stats = await app._deliver_summaries(
        summaries=_summaries(), categories=["politica"], hour=None
    )

    assert sent_count == 9
    assert stats["sent_by_channel"]["whatsapp"] == 9
    assert max_in_flight <= 3
    # confirma que de verdad hubo solapamiento (no quedo serializado por accidente)
    assert max_in_flight >= 2


@pytest.mark.asyncio
async def test_deliver_summaries_defaults_to_five_when_setting_missing():
    """`getattr(self.settings, "delivery_concurrency", 5)` covers settings
    objects (like some test doubles) that don't define the field at all."""

    subscribers = [_subscriber(i) for i in range(3)]
    settings = _settings()
    del settings.delivery_concurrency
    app = NewsSummarizerApp(settings)
    app.db = SubscriberDatabase(subscribers)
    app.whatsapp = _AlwaysSendsWhatsApp()

    sent_count, _stats = await app._deliver_summaries(
        summaries=_summaries(), categories=["politica"], hour=None
    )

    assert sent_count == 3


class _AlwaysSendsWhatsApp:
    async def send_message(self, to, message):
        return True


@pytest.mark.asyncio
async def test_deliver_summaries_isolates_one_subscriber_failing_from_the_rest():
    subscribers = [_subscriber(0), _subscriber(1), _subscriber(2)]

    class FlakyWhatsApp:
        async def send_message(self, to, message):
            if to == subscribers[1].phone:
                raise RuntimeError("fallo de red")
            return True

    app = NewsSummarizerApp(_settings())
    app.db = SubscriberDatabase(subscribers)
    app.whatsapp = FlakyWhatsApp()

    sent_count, stats = await app._deliver_summaries(
        summaries=_summaries(), categories=["politica"], hour=None
    )

    # el que fallo no se cuenta ni como enviado ni como fallido (misma
    # semantica que el loop secuencial de antes -- ver
    # tests/test_delivery_sentry_reporting.py), pero los otros dos si.
    assert sent_count == 2
    assert stats["sent_by_channel"]["whatsapp"] == 2
    assert stats["failed_by_channel"]["whatsapp"] == 0


@pytest.mark.asyncio
async def test_deliver_summaries_handles_mixed_channels_concurrently():
    subscribers = [
        _subscriber(0, "whatsapp"),
        _subscriber(1, "telegram"),
        _subscriber(2, "email"),
    ]
    app = NewsSummarizerApp(_settings())
    app.db = SubscriberDatabase(subscribers)
    app.whatsapp = _AlwaysSendsWhatsApp()

    class AlwaysSendsTelegram:
        async def send_message(self, chat_id, message):
            return True

    class AlwaysSendsEmail:
        async def send_message(self, email, subject, body, html_body=None):
            return True

    app.telegram = AlwaysSendsTelegram()
    app.email = AlwaysSendsEmail()

    sent_count, stats = await app._deliver_summaries(
        summaries=_summaries(), categories=["politica"], hour=None
    )

    assert sent_count == 3
    assert stats["sent_by_channel"] == {"whatsapp": 1, "telegram": 1, "email": 1}
