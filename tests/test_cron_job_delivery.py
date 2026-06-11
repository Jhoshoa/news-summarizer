import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

CRON_SRC = Path(__file__).resolve().parents[1] / "cron-job" / "src"
if str(CRON_SRC) not in sys.path:
    sys.path.insert(0, str(CRON_SRC))

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
