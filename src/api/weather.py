from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from src.collectors.weather import OpenMeteoWeatherCollector, WeatherLocationResolver


def create_weather_router() -> APIRouter:
    router = APIRouter(prefix="/api/weather", tags=["weather"])
    resolver = WeatherLocationResolver()

    @router.get("")
    async def get_weather(
        request: Request,
        location: Annotated[
            str | None,
            Query(
                description=(
                    "Ubicación o departamento de Bolivia. Si se omite, intenta resolver por "
                    "headers y cae a La Paz."
                ),
            ),
        ] = None,
    ):
        selected_location = resolver.resolve(
            requested_location=location,
            headers=dict(request.headers),
        )
        collector = OpenMeteoWeatherCollector()

        try:
            weather = await collector.fetch_current(selected_location)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"No se pudo obtener clima desde Open-Meteo: {exc}",
            ) from exc

        return weather

    @router.get("/locations")
    async def get_weather_locations():
        return {"items": resolver.available_locations()}

    return router
