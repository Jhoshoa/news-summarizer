from datetime import date
from types import SimpleNamespace

from src.api.articles import _today_for_app
from src.main import app


def test_economic_indicators_endpoint_documents_date_query_param():
    schema = app.openapi()
    parameters = schema["paths"]["/api/economic-indicators"]["get"]["parameters"]

    date_param = next(param for param in parameters if param["name"] == "date")

    assert date_param["in"] == "query"
    assert date_param["required"] is False
    assert {"type": "string", "format": "date"} in date_param["schema"]["anyOf"]


def test_articles_endpoint_documents_date_query_param():
    schema = app.openapi()
    parameters = schema["paths"]["/api/articles"]["get"]["parameters"]

    date_param = next(param for param in parameters if param["name"] == "date")

    assert date_param["in"] == "query"
    assert date_param["required"] is False
    assert {"type": "string", "format": "date"} in date_param["schema"]["anyOf"]


def test_articles_today_falls_back_when_timezone_is_invalid():
    app_instance = SimpleNamespace(settings=SimpleNamespace(schedule_timezone="Invalid/Zone"))

    assert isinstance(_today_for_app(app_instance), date)
