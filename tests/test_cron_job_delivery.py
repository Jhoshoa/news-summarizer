import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import httpx
import pytest

CRON_SRC = Path(__file__).resolve().parents[1] / "cron-job" / "src"
if str(CRON_SRC) not in sys.path:
    sys.path.insert(0, str(CRON_SRC))

import news_cron.jobs.runner as runner_module  # noqa: E402
from news_cron.clients.backend import BackendClient, BackendRequestError  # noqa: E402
from news_cron.config.settings import (  # noqa: E402
    DELIVERY_MAX_HOUR,
    DELIVERY_MIN_HOUR,
    CronSettings,
    _env_delivery_hours,
)
from news_cron.jobs.runner import RefreshJobRunner  # noqa: E402


def test_cron_settings_defaults_keep_summary_and_delivery_separate(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://backend:8000")
    monkeypatch.setenv("API_AUTH_KEY", "test-api-auth-key-value")
    monkeypatch.delenv("SUMMARY_TRIGGER_PATH", raising=False)
    monkeypatch.delenv("DELIVERY_TRIGGER_PATH", raising=False)
    monkeypatch.delenv("DELIVERY_HOURS", raising=False)

    settings = CronSettings.from_env()

    assert settings.summary_trigger_path == "/trigger/summary"
    assert settings.delivery_trigger_path == "/trigger/delivery"
    assert settings.delivery_hours == list(range(DELIVERY_MIN_HOUR, DELIVERY_MAX_HOUR + 1))


@pytest.mark.asyncio
async def test_cron_summary_refresh_uses_async_mode_and_polls_until_success(monkeypatch):
    """El refresh de resumenes ahora dispara en async_mode y sondea el job
    hasta que termine, en vez de un solo POST bloqueante -- un pipeline que
    tarda mas que SUMMARY_REQUEST_TIMEOUT_SECONDS ya no se marca como fallo
    y reintentado (lo que antes lanzaba una segunda corrida encima de la que
    seguia viva en el backend)."""

    settings = SimpleNamespace(
        summary_time_of_day="night",
        summary_trigger_path="/trigger/summary",
        summary_request_timeout_seconds=30,
        summary_poll_interval_seconds=0,
        summary_job_max_wait_seconds=60,
    )
    runner = RefreshJobRunner.__new__(RefreshJobRunner)
    runner.settings = settings
    calls = []

    async def post_json(path, *, timeout_seconds):
        calls.append(("POST", path, timeout_seconds))
        return {
            "status": "accepted",
            "job": {"id": "job-1", "status": "queued"},
            "status_url": "/trigger/summary/jobs/job-1",
        }

    statuses = iter(["running", "success"])

    async def get_json(path, *, timeout_seconds):
        calls.append(("GET", path, timeout_seconds))
        status = next(statuses)
        job = {"id": "job-1", "status": status}
        if status == "success":
            job["result"] = {"summaries": 2, "sent": 1}
        return {"status": status, "job": job}

    runner.backend = SimpleNamespace(post_json=post_json, get_json=get_json)

    await runner.run_summary_refresh()

    assert calls[0] == ("POST", "/trigger/summary?time_of_day=night&refresh=true&async_mode=true", 30)
    assert calls[1] == ("GET", "/trigger/summary/jobs/job-1", 30)
    assert calls[2] == ("GET", "/trigger/summary/jobs/job-1", 30)


@pytest.mark.asyncio
async def test_cron_summary_refresh_raises_when_job_fails(monkeypatch):
    settings = SimpleNamespace(
        summary_time_of_day="manual",
        summary_trigger_path="/trigger/summary",
        summary_request_timeout_seconds=30,
        summary_poll_interval_seconds=0,
        summary_job_max_wait_seconds=60,
    )
    runner = RefreshJobRunner.__new__(RefreshJobRunner)
    runner.settings = settings

    async def post_json(path, *, timeout_seconds):
        return {
            "job": {"id": "job-2", "status": "queued"},
            "status_url": "/trigger/summary/jobs/job-2",
        }

    async def get_json(path, *, timeout_seconds):
        return {"job": {"id": "job-2", "status": "failed", "error_message": "boom"}}

    runner.backend = SimpleNamespace(post_json=post_json, get_json=get_json)

    with pytest.raises(BackendRequestError) as exc_info:
        await runner.run_summary_refresh()

    assert "boom" in str(exc_info.value.last_error)


@pytest.mark.asyncio
async def test_poll_summary_job_fetches_result_when_already_finished():
    """Si el job ya termino cuando llega la respuesta del POST inicial (por
    ejemplo, el candado de concurrencia del backend devolvio un job en
    curso que resulto terminar casi de inmediato), no hay que sondear -- pero
    igual hay que traer el resultado completo con un GET."""

    settings = SimpleNamespace(
        summary_poll_interval_seconds=0,
        summary_job_max_wait_seconds=60,
        summary_request_timeout_seconds=30,
    )
    runner = RefreshJobRunner.__new__(RefreshJobRunner)
    runner.settings = settings
    calls = []

    async def get_json(path, *, timeout_seconds):
        calls.append(path)
        return {"job": {"id": "job-4", "status": "success", "result": {"summaries": 5}}}

    runner.backend = SimpleNamespace(get_json=get_json)

    result = await runner._poll_summary_job("/trigger/summary/jobs/job-4", initial_status="success")

    assert result == {"summaries": 5}
    assert calls == ["/trigger/summary/jobs/job-4"]


@pytest.mark.asyncio
async def test_poll_summary_job_raises_when_max_wait_exceeded(monkeypatch):
    settings = SimpleNamespace(summary_poll_interval_seconds=0, summary_job_max_wait_seconds=10)
    runner = RefreshJobRunner.__new__(RefreshJobRunner)
    runner.settings = settings

    times = iter(
        [
            datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            datetime(2026, 1, 1, 12, 0, 20, tzinfo=UTC),
        ]
    )
    monkeypatch.setattr(runner_module, "utc_now", lambda: next(times))

    async def get_json(path, *, timeout_seconds):
        raise AssertionError("no deberia sondear si ya paso el tiempo maximo")

    runner.backend = SimpleNamespace(get_json=get_json)

    with pytest.raises(BackendRequestError):
        await runner._poll_summary_job("/trigger/summary/jobs/job-3", initial_status="running")


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

    await runner.run_delivery_window(16)

    assert calls == [("/trigger/delivery?hour=16", 45)]


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


def test_cron_delivery_hours_env_overrides_default_range(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://backend:8000")
    monkeypatch.setenv("API_AUTH_KEY", "test-api-auth-key-value")
    monkeypatch.setenv("DELIVERY_HOURS", "9, 15,23")

    settings = CronSettings.from_env()

    assert settings.delivery_hours == [9, 15, 23]


def test_env_delivery_hours_rejects_hour_outside_9_23(monkeypatch):
    monkeypatch.setenv("DELIVERY_HOURS", "5")

    with pytest.raises(ValueError, match="9-23"):
        _env_delivery_hours()


def test_env_delivery_hours_rejects_hour_24_and_negative(monkeypatch):
    for bad_value in ("24", "-1"):
        monkeypatch.setenv("DELIVERY_HOURS", bad_value)
        with pytest.raises(ValueError):
            _env_delivery_hours()


def test_next_delivery_run_picks_todays_hour_when_still_ahead():
    settings = SimpleNamespace(schedule_timezone="America/La_Paz")
    runner = RefreshJobRunner.__new__(RefreshJobRunner)
    runner.settings = settings
    bolivia = ZoneInfo("America/La_Paz")
    now = datetime(2026, 8, 26, 14, 0, tzinfo=bolivia).astimezone(UTC)

    next_run = runner._next_delivery_run(15, after=now)

    assert next_run.astimezone(bolivia) == datetime(2026, 8, 26, 15, 0, tzinfo=bolivia)


def test_next_delivery_run_rolls_over_to_tomorrow_when_hour_already_passed():
    settings = SimpleNamespace(schedule_timezone="America/La_Paz")
    runner = RefreshJobRunner.__new__(RefreshJobRunner)
    runner.settings = settings
    bolivia = ZoneInfo("America/La_Paz")
    now = datetime(2026, 8, 26, 14, 0, tzinfo=bolivia).astimezone(UTC)

    next_run = runner._next_delivery_run(9, after=now)

    assert next_run.astimezone(bolivia) == datetime(2026, 8, 27, 9, 0, tzinfo=bolivia)


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
