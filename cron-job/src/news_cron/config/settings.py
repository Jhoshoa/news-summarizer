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
    summary_time_of_day: str
    summary_trigger_path: str
    delivery_trigger_path: str
    delivery_morning_at: str | None
    delivery_afternoon_at: str | None
    delivery_night_at: str | None
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
            summary_time_of_day=os.getenv("SUMMARY_TIME_OF_DAY", "manual").strip() or "manual",
            summary_trigger_path=_env_path("SUMMARY_TRIGGER_PATH", default="/trigger/summary"),
            delivery_trigger_path=_env_path("DELIVERY_TRIGGER_PATH", default="/trigger/delivery"),
            delivery_morning_at=_env_delivery_time(
                "DELIVERY_MORNING_AT",
                legacy_name="SCHEDULE_SUMMARY_MORNING",
                default="09:00",
            ),
            delivery_afternoon_at=_env_delivery_time(
                "DELIVERY_AFTERNOON_AT",
                legacy_name="SCHEDULE_SUMMARY_AFTERNOON",
                default="16:00",
            ),
            delivery_night_at=_env_delivery_time(
                "DELIVERY_NIGHT_AT",
                legacy_name="SCHEDULE_SUMMARY_NIGHT",
                default="20:00",
            ),
            schedule_timezone=_env_timezone("SCHEDULE_TIMEZONE", default="America/La_Paz"),
        )

    def delivery_windows(self) -> dict[str, str]:
        return {
            window: scheduled_at
            for window, scheduled_at in {
                "morning": self.delivery_morning_at,
                "afternoon": self.delivery_afternoon_at,
                "night": self.delivery_night_at,
            }.items()
            if scheduled_at
        }


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


def _env_daily_time(name: str, *, default: str) -> str | None:
    raw = os.getenv(name, default).strip()
    if not raw:
        return None

    parts = raw.split(":")
    if len(parts) != 2:
        raise ValueError(f"{name} must use HH:MM format")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise ValueError(f"{name} must use HH:MM format") from exc
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"{name} must be a valid 24-hour time")
    return f"{hour:02d}:{minute:02d}"


def _env_delivery_time(name: str, *, legacy_name: str, default: str) -> str | None:
    if os.getenv(name) is not None:
        return _env_daily_time(name, default=default)
    return _env_daily_time(legacy_name, default=default)


def _env_timezone(name: str, *, default: str) -> str:
    value = os.getenv(name, default).strip() or default
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"{name} must be a valid IANA timezone") from exc
    return value
