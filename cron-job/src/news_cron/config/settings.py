from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class CronSettings:
    backend_base_url: str
    api_auth_key: str
    run_once: bool
    economic_refresh_interval_seconds: int
    summary_refresh_interval_seconds: int | None
    summary_refresh_hours: list[int] | None
    economic_request_timeout_seconds: float
    summary_request_timeout_seconds: float
    delivery_request_timeout_seconds: float
    request_retries: int
    summary_poll_interval_seconds: float
    summary_job_max_wait_seconds: float
    summary_time_of_day: str
    summary_trigger_path: str
    delivery_trigger_path: str
    delivery_hours: list[int]
    schedule_timezone: str

    @classmethod
    def from_env(cls) -> CronSettings:
        api_auth_key = _required_env("API_AUTH_KEY")
        if len(api_auth_key) < 16:
            raise ValueError("API_AUTH_KEY must be at least 16 characters long")

        summary_refresh_hours = _env_summary_hours()
        summary_refresh_interval_seconds = (
            _env_interval_seconds(
                prefix="SUMMARY_REFRESH",
                default_minutes=180,
                minimum_seconds=60,
            )
            if summary_refresh_hours is None
            else None
        )

        return cls(
            backend_base_url=_required_env("BACKEND_BASE_URL").rstrip("/"),
            api_auth_key=api_auth_key,
            run_once=_env_bool("RUN_ONCE", default=False),
            economic_refresh_interval_seconds=_env_interval_seconds(
                prefix="ECONOMIC_REFRESH",
                default_minutes=60,
                minimum_seconds=60,
            ),
            summary_refresh_interval_seconds=summary_refresh_interval_seconds,
            summary_refresh_hours=summary_refresh_hours,
            economic_request_timeout_seconds=float(
                _env_timeout_seconds(
                    "ECONOMIC_REQUEST_TIMEOUT_SECONDS",
                    default=60,
                    minimum=10,
                )
            ),
            summary_request_timeout_seconds=float(
                _env_timeout_seconds(
                    "SUMMARY_REQUEST_TIMEOUT_SECONDS",
                    default=180,
                    minimum=30,
                )
            ),
            delivery_request_timeout_seconds=float(
                _env_timeout_seconds(
                    "DELIVERY_REQUEST_TIMEOUT_SECONDS",
                    default=180,
                    minimum=30,
                )
            ),
            request_retries=_env_int("REQUEST_RETRIES", default=2, minimum=0),
            summary_poll_interval_seconds=float(
                _env_int("SUMMARY_POLL_INTERVAL_SECONDS", default=15, minimum=5)
            ),
            summary_job_max_wait_seconds=float(
                _env_int("SUMMARY_JOB_MAX_WAIT_SECONDS", default=1800, minimum=60)
            ),
            summary_time_of_day=os.getenv("SUMMARY_TIME_OF_DAY", "manual").strip() or "manual",
            summary_trigger_path=_env_path("SUMMARY_TRIGGER_PATH", default="/trigger/summary"),
            delivery_trigger_path=_env_path("DELIVERY_TRIGGER_PATH", default="/trigger/delivery"),
            delivery_hours=_env_delivery_hours(),
            schedule_timezone=_env_timezone("SCHEDULE_TIMEZONE", default="America/La_Paz"),
        )


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _env_int(name: str, *, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_interval_seconds(
    *,
    prefix: str,
    default_minutes: int,
    minimum_seconds: int,
) -> int:
    every_name = f"{prefix}_EVERY"
    unit_name = f"{prefix}_UNIT"
    legacy_minutes_name = f"{prefix}_INTERVAL_MINUTES"

    if os.getenv(every_name):
        every = _env_int(every_name, default=1, minimum=1)
        unit = os.getenv(unit_name, "minutes").strip().lower()
        unit_multipliers = {
            "second": 1,
            "seconds": 1,
            "minute": 60,
            "minutes": 60,
            "hour": 3600,
            "hours": 3600,
        }
        if unit not in unit_multipliers:
            raise ValueError(f"{unit_name} must be seconds, minutes, or hours")
        seconds = every * unit_multipliers[unit]
    else:
        seconds = _env_int(
            legacy_minutes_name,
            default=default_minutes,
            minimum=1,
        ) * 60

    if seconds < minimum_seconds:
        raise ValueError(f"{prefix} interval must be >= {minimum_seconds} seconds")
    return seconds


def _env_summary_hours() -> list[int] | None:
    raw = os.getenv("SUMMARY_REFRESH_HOURS")
    if raw is None or raw.strip() == "":
        return None
    hours: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            hour = int(part)
        except ValueError as exc:
            raise ValueError(f"SUMMARY_REFRESH_HOURS must be comma-separated hours (0-23), got '{part}'") from exc
        if not 0 <= hour <= 23:
            raise ValueError(f"SUMMARY_REFRESH_HOURS hour must be 0-23, got {hour}")
        hours.append(hour)
    if not hours:
        raise ValueError("SUMMARY_REFRESH_HOURS is set but no valid hours found")
    return sorted(hours)


def _env_timeout_seconds(name: str, *, default: int, minimum: int) -> int:
    if os.getenv(name):
        return _env_int(name, default=default, minimum=minimum)
    return _env_int("REQUEST_TIMEOUT_SECONDS", default=default, minimum=minimum)


def _env_path(name: str, *, default: str) -> str:
    value = os.getenv(name, default).strip() or default
    if not value.startswith("/"):
        raise ValueError(f"{name} must start with /")
    return value


DELIVERY_MIN_HOUR = 9
DELIVERY_MAX_HOUR = 23


def _env_delivery_hours() -> list[int]:
    """Hours (24h, subscriber's local time) the cron fires a delivery run for.

    Each subscriber only receives a message when their own preferred_hour
    matches the hour a run fires for -- see _matches_preferred_hour in the
    backend. Defaults to every hour in [DELIVERY_MIN_HOUR, DELIVERY_MAX_HOUR]:
    outside that range there's little fresh news to send, and the /suscribirse
    form doesn't let subscribers pick an hour outside it either.
    """

    raw = os.getenv("DELIVERY_HOURS")
    if raw is None or raw.strip() == "":
        return list(range(DELIVERY_MIN_HOUR, DELIVERY_MAX_HOUR + 1))

    hours: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            hour = int(part)
        except ValueError as exc:
            raise ValueError(f"DELIVERY_HOURS must be comma-separated hours ({DELIVERY_MIN_HOUR}-{DELIVERY_MAX_HOUR}), got '{part}'") from exc
        if not DELIVERY_MIN_HOUR <= hour <= DELIVERY_MAX_HOUR:
            raise ValueError(f"DELIVERY_HOURS hour must be {DELIVERY_MIN_HOUR}-{DELIVERY_MAX_HOUR}, got {hour}")
        hours.append(hour)
    if not hours:
        raise ValueError("DELIVERY_HOURS is set but no valid hours found")
    return sorted(set(hours))


def _env_timezone(name: str, *, default: str) -> str:
    value = os.getenv(name, default).strip() or default
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"{name} must be a valid IANA timezone") from exc
    return value
