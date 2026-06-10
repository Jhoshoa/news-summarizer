from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CronSettings:
    backend_base_url: str
    api_auth_key: str
    run_once: bool
    economic_refresh_interval_seconds: int
    summary_refresh_interval_seconds: int
    economic_request_timeout_seconds: float
    summary_request_timeout_seconds: float
    request_retries: int
    summary_time_of_day: str

    @classmethod
    def from_env(cls) -> CronSettings:
        api_auth_key = _required_env("API_AUTH_KEY")
        if len(api_auth_key) < 16:
            raise ValueError("API_AUTH_KEY must be at least 16 characters long")

        return cls(
            backend_base_url=_required_env("BACKEND_BASE_URL").rstrip("/"),
            api_auth_key=api_auth_key,
            run_once=_env_bool("RUN_ONCE", default=False),
            economic_refresh_interval_seconds=_env_interval_seconds(
                prefix="ECONOMIC_REFRESH",
                default_minutes=60,
                minimum_seconds=60,
            ),
            summary_refresh_interval_seconds=_env_interval_seconds(
                prefix="SUMMARY_REFRESH",
                default_minutes=180,
                minimum_seconds=60,
            ),
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
            request_retries=_env_int("REQUEST_RETRIES", default=2, minimum=0),
            summary_time_of_day=os.getenv("SUMMARY_TIME_OF_DAY", "manual").strip() or "manual",
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


def _env_timeout_seconds(name: str, *, default: int, minimum: int) -> int:
    if os.getenv(name):
        return _env_int(name, default=default, minimum=minimum)
    return _env_int("REQUEST_TIMEOUT_SECONDS", default=default, minimum=minimum)
