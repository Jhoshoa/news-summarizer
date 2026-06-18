from types import SimpleNamespace

import pytest

from src.scheduler.cron import NewsScheduler


class FakeScheduler:
    def __init__(self):
        self.jobs = []
        self.started = False
        self.shutdown_called = False

    def add_job(self, func, trigger, args, id, replace_existing, name):  # noqa: A002
        self.jobs.append(
            {
                "args": args,
                "func": func,
                "id": id,
                "name": name,
                "replace_existing": replace_existing,
                "trigger": trigger,
            }
        )

    def start(self):
        self.started = True

    def shutdown(self):
        self.shutdown_called = True

    def get_jobs(self):
        return self.jobs


def test_scheduler_registers_three_summary_windows():
    settings = SimpleNamespace(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        schedule_timezone="America/La_Paz",
        schedule_summary_morning="09:00",
        schedule_summary_afternoon="16:00",
        schedule_summary_night="20:00",
        schedule_summary_evening=None,
    )
    scheduler = NewsScheduler(app=object(), settings=settings)
    fake_scheduler = FakeScheduler()
    scheduler.scheduler = fake_scheduler

    scheduler.start()

    assert fake_scheduler.started is True
    assert [job["id"] for job in fake_scheduler.jobs] == [
        "morning_summary",
        "afternoon_summary",
        "night_summary",
    ]
    assert [job["args"] for job in fake_scheduler.jobs] == [
        ["morning"],
        ["afternoon"],
        ["night"],
    ]


def test_scheduler_keeps_legacy_evening_job_when_configured():
    settings = SimpleNamespace(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        schedule_timezone="America/La_Paz",
        schedule_summary_morning=None,
        schedule_summary_afternoon=None,
        schedule_summary_night=None,
        schedule_summary_evening="18:00",
    )
    scheduler = NewsScheduler(app=object(), settings=settings)
    fake_scheduler = FakeScheduler()
    scheduler.scheduler = fake_scheduler

    scheduler.start()

    assert [job["id"] for job in fake_scheduler.jobs] == ["evening_summary"]
    assert fake_scheduler.jobs[0]["args"] == ["evening"]


@pytest.mark.asyncio
async def test_scheduler_window_uses_cached_delivery():
    calls = []

    async def deliver_cached_summaries(time_of_day):
        calls.append(time_of_day)

    async def send_summaries(time_of_day):
        raise AssertionError("Scheduler windows should not generate summaries")

    settings = SimpleNamespace(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        schedule_timezone="America/La_Paz",
        schedule_summary_morning=None,
        schedule_summary_afternoon=None,
        schedule_summary_night=None,
        schedule_summary_evening=None,
    )
    app = SimpleNamespace(
        deliver_cached_summaries=deliver_cached_summaries,
        send_summaries=send_summaries,
    )
    scheduler = NewsScheduler(app=app, settings=settings)

    await scheduler._send_summary_for_window("night")

    assert calls == ["night"]
