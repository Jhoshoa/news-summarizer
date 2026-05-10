from src.collectors.weather import OpenMeteoWeatherCollector, WeatherLocationResolver
from src.main import app


def test_weather_location_resolver_defaults_to_la_paz():
    resolver = WeatherLocationResolver()

    location = resolver.resolve()

    assert location.key == "la_paz"
    assert location.department == "La Paz"


def test_weather_location_resolver_uses_requested_location_before_headers():
    resolver = WeatherLocationResolver()

    location = resolver.resolve(
        requested_location="Cochabamba",
        headers={"x-vercel-ip-city": "Santa Cruz", "cf-ipcountry": "BO"},
    )

    assert location.key == "cochabamba"


def test_weather_location_resolver_uses_supported_location_headers():
    resolver = WeatherLocationResolver()

    location = resolver.resolve(headers={"x-vercel-ip-region": "Tarija", "cf-ipcountry": "BO"})

    assert location.key == "tarija"


def test_weather_location_resolver_ignores_non_bolivia_headers():
    resolver = WeatherLocationResolver()

    location = resolver.resolve(headers={"x-vercel-ip-region": "Tarija", "cf-ipcountry": "US"})

    assert location.key == "la_paz"


def test_open_meteo_response_is_normalized_for_frontend():
    collector = OpenMeteoWeatherCollector()
    resolver = WeatherLocationResolver()
    location = resolver.resolve(requested_location="La Paz")

    result = collector._normalize_response(
        location,
        {
            "current": {"temperature_2m": 13.5},
            "current_units": {"temperature_2m": "°C"},
            "hourly": {
                "uv_index": [9.1],
                "uv_index_clear_sky": [10.0],
                "shortwave_radiation": [730],
                "direct_radiation": [600],
            },
            "hourly_units": {"uv_index": ""},
            "daily": {
                "temperature_2m_max": [18.0],
                "temperature_2m_min": [5.0],
                "uv_index_max": [11.2],
                "precipitation_sum": [0.0],
            },
            "daily_units": {"temperature_2m_max": "°C"},
        },
    )

    assert result["location"]["key"] == "la_paz"
    assert result["current"]["temperature_2m"] == 13.5
    assert result["radiation"]["uv_index"] == 9.1
    assert result["today"]["uv_index_max"] == 11.2


def test_weather_endpoint_documents_location_query_param():
    schema = app.openapi()
    parameters = schema["paths"]["/api/weather"]["get"]["parameters"]

    location_param = next(param for param in parameters if param["name"] == "location")

    assert location_param["in"] == "query"
    assert location_param["required"] is False
