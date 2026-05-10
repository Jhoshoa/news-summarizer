from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class WeatherLocation:
    key: str
    name: str
    department: str
    country: str
    latitude: float
    longitude: float


BOLIVIA_WEATHER_LOCATIONS: dict[str, WeatherLocation] = {
    "la_paz": WeatherLocation("la_paz", "La Paz", "La Paz", "Bolivia", -16.5, -68.15),
    "santa_cruz": WeatherLocation(
        "santa_cruz", "Santa Cruz", "Santa Cruz", "Bolivia", -17.78, -63.18
    ),
    "cochabamba": WeatherLocation(
        "cochabamba", "Cochabamba", "Cochabamba", "Bolivia", -17.39, -66.16
    ),
    "oruro": WeatherLocation("oruro", "Oruro", "Oruro", "Bolivia", -17.96, -67.11),
    "potosi": WeatherLocation("potosi", "Potosi", "Potosi", "Bolivia", -19.58, -65.75),
    "tarija": WeatherLocation("tarija", "Tarija", "Tarija", "Bolivia", -21.53, -64.73),
    "sucre": WeatherLocation("sucre", "Sucre", "Chuquisaca", "Bolivia", -19.03, -65.26),
    "trinidad": WeatherLocation("trinidad", "Trinidad", "Beni", "Bolivia", -14.83, -64.9),
    "cobija": WeatherLocation("cobija", "Cobija", "Pando", "Bolivia", -11.03, -68.77),
}


class WeatherLocationResolver:
    DEFAULT_LOCATION_KEY = "la_paz"

    HEADER_CANDIDATES = (
        "x-vercel-ip-city",
        "x-vercel-ip-region",
        "x-appengine-city",
        "x-appengine-region",
        "cf-ipcity",
        "cf-region",
    )

    def resolve(
        self,
        *,
        requested_location: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> WeatherLocation:
        if requested_location:
            match = self._match_location(requested_location)
            if match:
                return match

        normalized_headers = {key.lower(): value for key, value in (headers or {}).items()}
        country = normalized_headers.get("cf-ipcountry") or normalized_headers.get(
            "x-vercel-ip-country"
        )
        if country and country.upper() not in {"BO", "BOL", "BOLIVIA"}:
            return BOLIVIA_WEATHER_LOCATIONS[self.DEFAULT_LOCATION_KEY]

        for header in self.HEADER_CANDIDATES:
            match = self._match_location(normalized_headers.get(header))
            if match:
                return match

        return BOLIVIA_WEATHER_LOCATIONS[self.DEFAULT_LOCATION_KEY]

    def available_locations(self) -> list[dict[str, Any]]:
        return [
            {
                "key": location.key,
                "name": location.name,
                "department": location.department,
                "country": location.country,
                "latitude": location.latitude,
                "longitude": location.longitude,
            }
            for location in BOLIVIA_WEATHER_LOCATIONS.values()
        ]

    def _match_location(self, value: str | None) -> WeatherLocation | None:
        if not value:
            return None

        normalized = self._normalize(value)
        for location in BOLIVIA_WEATHER_LOCATIONS.values():
            aliases = {
                self._normalize(location.key),
                self._normalize(location.name),
                self._normalize(location.department),
            }
            if normalized in aliases:
                return location

        return None

    def _normalize(self, value: str) -> str:
        return value.strip().lower().replace(" ", "_").replace("-", "_")


class OpenMeteoWeatherCollector:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    async def fetch_current(self, location: WeatherLocation) -> dict[str, Any]:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                ]
            ),
            "hourly": ",".join(
                [
                    "uv_index",
                    "uv_index_clear_sky",
                    "shortwave_radiation",
                    "direct_radiation",
                ]
            ),
            "daily": ",".join(
                [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "uv_index_max",
                    "precipitation_sum",
                ]
            ),
            "forecast_days": 1,
            "timezone": "America/La_Paz",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        return self._normalize_response(location, data)

    def _normalize_response(
        self,
        location: WeatherLocation,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        current = data.get("current") or {}
        hourly = data.get("hourly") or {}
        daily = data.get("daily") or {}

        return {
            "location": {
                "key": location.key,
                "name": location.name,
                "department": location.department,
                "country": location.country,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "current": current,
            "today": {
                "temperature_max": self._first(daily.get("temperature_2m_max")),
                "temperature_min": self._first(daily.get("temperature_2m_min")),
                "uv_index_max": self._first(daily.get("uv_index_max")),
                "precipitation_sum": self._first(daily.get("precipitation_sum")),
            },
            "radiation": {
                "uv_index": self._first(hourly.get("uv_index")),
                "uv_index_clear_sky": self._first(hourly.get("uv_index_clear_sky")),
                "shortwave_radiation": self._first(hourly.get("shortwave_radiation")),
                "direct_radiation": self._first(hourly.get("direct_radiation")),
            },
            "units": {
                "current": data.get("current_units") or {},
                "hourly": data.get("hourly_units") or {},
                "daily": data.get("daily_units") or {},
            },
            "raw_payload": data,
        }

    def _first(self, values: list[Any] | None) -> Any:
        if not values:
            return None
        return values[0]
