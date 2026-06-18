import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

CRON_SRC = Path(__file__).resolve().parents[1] / "cron-job" / "src"
if str(CRON_SRC) not in sys.path:
    sys.path.insert(0, str(CRON_SRC))

import news_cron.jobs.runner as runner_module  # noqa: E402
from news_cron.clients.backend import BackendClient, BackendRequestError  # noqa: E402
from news_cron.config.settings import CronSettings  # noqa: E402
from news_cron.jobs.runner import RefreshJobRunner  # noqa: E402


def test_cron_settings_defaults_keep_summary_and_delivery_separate(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://backend:8000")
    monkeypatch.setenv("API_AUTH_KEY", "test-api-auth-key-value")
    monkeypatch.delenv("SUMMARY_TRIGGER_PATH", raising=False)
    monkeypatch.delenv("DELIVERY_TRIGGER_PATH", raising=False)

    settings = CronSettings.from_env()

    assert settings.summary_trigger_path == "/trigger/summary"
    assert settings.delivery_trigger_path == "/trigger/delivery"
    assert settings.delivery_windows() == {
        "morning": "09:00",
        "afternoon": "16:00",
        "night": "20:00",
    }


@pytest.mark.asyncio
async def test_cron_summary_refresh_uses_summary_endpoint(monkeypatch):
    settings = SimpleNamespace(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        summary_time_of_day="night",
        summary_trigger_path="/trigger/summary",
        summary_request_timeout_seconds=30,
    )
    runner = RefreshJobRunner.__new__(RefreshJobRunner)
    runner.settings = settings
    calls = []

    async def post_json(path, *, timeout_seconds):
        calls.append((path, timeout_seconds))
        return {"result": {"summaries": 2, "sent": 1}}

    runner.backend = SimpleNamespace(post_json=post_json)

    await runner.run_summary_refresh()

    assert calls == [("/trigger/summary?time_of_day=night&refresh=true", 30)]


@pytest.mark.asyncio
async def test_cron_delivery_window_uses_delivery_endpoint(monkeypatch):
    settings = SimpleNamespace(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        delivery_trigger_path="/trigger/delivery",
        delivery_request_timeout_seconds=45,
    )
    runner = RefreshJobRunner.__new__(RefreshJobRunner)
    runner.settings = settings
    calls = []

    async def post_json(path, *, timeout_seconds):
        calls.append((path, timeout_seconds))
        return {"result": {"summaries": 2, "sent": 1}}

    runner.backend = SimpleNamespace(post_json=post_json)

    await runner.run_delivery_window("afternoon")

    assert calls == [("/trigger/delivery?time_of_day=afternoon", 45)]


@pytest.mark.asyncio
async def test_backend_client_turns_backend_down_into_controlled_error():
    settings = SimpleNamespace(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        backend_base_url="http://backend:8000",
        api_auth_key="test-api-auth-key-value",
        request_retries=0,
    )
    client = BackendClient(settings)

    async def handler(request):
        raise httpx.ConnectError("All connection attempts failed", request=request)

    await client.client.aclose()
    client.client = httpx.AsyncClient(
        base_url=settings.backend_base_url,
        transport=httpx.MockTransport(handler),
    )

    try:
        with pytest.raises(BackendRequestError) as exc_info:
            await client.post_json("/api/economic-indicators/refresh", timeout_seconds=10)

        assert exc_info.value.path == "/api/economic-indicators/refresh"
        assert exc_info.value.attempts == 1
        assert isinstance(exc_info.value.last_error, httpx.ConnectError)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_run_safely_logs_controlled_backend_failure_without_traceback(caplog):
    runner = RefreshJobRunner.__new__(RefreshJobRunner)
    error = BackendRequestError(
        "/trigger/summary?time_of_day=manual&refresh=true",
        3,
        httpx.ConnectError("All connection attempts failed"),
    )

    async def failing_job():
        raise error

    with caplog.at_level("ERROR", logger="news_summarizer_cron"):
        ok = await runner._run_safely("summary_refresh", failing_job())

    assert ok is False
    assert "job failed name=summary_refresh" in caplog.text
    assert "Traceback" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_cron_delivery_time_accepts_blank_to_disable_window(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://backend:8000")
    monkeypatch.setenv("API_AUTH_KEY", "test-api-auth-key-value")
    monkeypatch.setenv("DELIVERY_MORNING_AT", "")
    monkeypatch.setenv("DELIVERY_AFTERNOON_AT", "15:05")
    monkeypatch.setenv("DELIVERY_NIGHT_AT", "")

    settings = CronSettings.from_env()

    assert settings.delivery_windows() == {"afternoon": "15:05"}


def test_cron_delivery_time_accepts_schedule_summary_aliases(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://backend:8000")
    monkeypatch.setenv("API_AUTH_KEY", "test-api-auth-key-value")
    monkeypatch.delenv("DELIVERY_MORNING_AT", raising=False)
    monkeypatch.delenv("DELIVERY_AFTERNOON_AT", raising=False)
    monkeypatch.delenv("DELIVERY_NIGHT_AT", raising=False)
    monkeypatch.setenv("SCHEDULE_SUMMARY_MORNING", "08:30")
    monkeypatch.setenv("SCHEDULE_SUMMARY_AFTERNOON", "15:45")
    monkeypatch.setenv("SCHEDULE_SUMMARY_NIGHT", "21:10")

    settings = CronSettings.from_env()

    assert settings.delivery_windows() == {
        "morning": "08:30",
        "afternoon": "15:45",
        "night": "21:10",
    }


def test_cron_summary_hours_disable_interval_mode(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://backend:8000")
    monkeypatch.setenv("API_AUTH_KEY", "test-api-auth-key-value")
    monkeypatch.setenv("SUMMARY_REFRESH_HOURS", "8,10,13,16,19,22")
    monkeypatch.setenv("SUMMARY_REFRESH_EVERY", "4")
    monkeypatch.setenv("SUMMARY_REFRESH_UNIT", "hours")

    settings = CronSettings.from_env()

    assert settings.summary_refresh_hours == [8, 10, 13, 16, 19, 22]
    assert settings.summary_refresh_interval_seconds is None


def test_fixed_summary_schedule_does_not_catch_up_current_hour_after_restart(monkeypatch):
    settings = SimpleNamespace(
        schedule_timezone="America/La_Paz",
        summary_refresh_hours=[8, 10, 13, 16, 19, 22],
    )
    runner = RefreshJobRunner.__new__(RefreshJobRunner)
    runner.settings = settings
    monkeypatch.setattr(
        runner_module,
        "utc_now",
        lambda: datetime(2026, 6, 18, 12, 30, tzinfo=UTC),
    )

    next_run = runner._next_summary_run()

    assert next_run == datetime(2026, 6, 18, 14, 0, tzinfo=UTC)
