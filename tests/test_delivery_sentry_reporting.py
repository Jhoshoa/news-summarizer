from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import sentry_sdk

from src.main import NewsSummarizerApp


def _make_app(*, db=None, telegram=None):
    settings = SimpleNamespace(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        categories_list=["politica"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
        telegram_webhook_url="https://ecobriefbolivia.online",
        telegram_webhook_secret="super-secret",
    )
    app = NewsSummarizerApp(settings)
    app.db = db
    app.telegram = telegram
    return app


class RaisingSubscribersDatabase:
    async def get_active_subscribers(self):
        raise RuntimeError("subscribers table unavailable")


class OneSubscriberDatabase:
    def __init__(self, subscriber):
        self.subscriber = subscriber

    async def get_active_subscribers(self):
        return [self.subscriber]


class RaisingWhatsApp:
    def send_message(self, to, message):
        raise RuntimeError("unexpected whatsapp failure")


class FakeBotThatFailsToRegister:
    async def set_webhook(self, *, url, secret_token):
        raise RuntimeError("telegram api unreachable")


@pytest.mark.asyncio
async def test_deliver_summaries_reports_subscriber_fetch_failure_to_sentry():
    app = _make_app(db=RaisingSubscribersDatabase())

    with patch.object(sentry_sdk, "capture_exception") as mock_capture:
        sent_count, _stats = await app._deliver_summaries(
            summaries=[], categories=["politica"], hour=None
        )

    assert sent_count == 0
    mock_capture.assert_called_once()
    assert isinstance(mock_capture.call_args.args[0], RuntimeError)


@pytest.mark.asyncio
async def test_deliver_summaries_reports_per_subscriber_failure_to_sentry():
    subscriber = SimpleNamespace(
        channel="whatsapp",
        phone="+591700000",
        categories=["politica"],
        preferred_hour=9,
        frequency="diario",
    )
    app = _make_app(db=OneSubscriberDatabase(subscriber))
    app.whatsapp = RaisingWhatsApp()

    with patch.object(sentry_sdk, "capture_exception") as mock_capture:
        sent_count, stats = await app._deliver_summaries(
            summaries=[{"title": "A", "summary": "resumen", "category": "politica"}],
            categories=["politica"],
            hour=None,
        )

    assert sent_count == 0
    assert stats["failed_by_channel"]["whatsapp"] == 0  # nunca llego a contarlo: exploto antes
    mock_capture.assert_called_once()
    assert isinstance(mock_capture.call_args.args[0], RuntimeError)


@pytest.mark.asyncio
async def test_register_telegram_webhook_reports_failure_to_sentry():
    telegram = SimpleNamespace(bot=FakeBotThatFailsToRegister())
    app = _make_app(telegram=telegram)

    with patch.object(sentry_sdk, "capture_exception") as mock_capture:
        await app._register_telegram_webhook()

    mock_capture.assert_called_once()
    assert isinstance(mock_capture.call_args.args[0], RuntimeError)


@pytest.mark.asyncio
async def test_register_telegram_webhook_noop_without_telegram_configured():
    app = _make_app(telegram=None)

    with patch.object(sentry_sdk, "capture_exception") as mock_capture:
        await app._register_telegram_webhook()

    mock_capture.assert_not_called()
