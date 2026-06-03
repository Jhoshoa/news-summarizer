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


def test_articles_endpoint_documents_fallback_query_param():
    schema = app.openapi()
    parameters = schema["paths"]["/api/articles"]["get"]["parameters"]

    fallback_param = next(param for param in parameters if param["name"] == "fallback_to_latest")

    assert fallback_param["in"] == "query"
    assert fallback_param["required"] is False
    assert fallback_param["schema"]["type"] == "boolean"
    assert fallback_param["schema"]["default"] is False


def test_articles_endpoint_documents_exclude_summarized_query_param():
    schema = app.openapi()
    parameters = schema["paths"]["/api/articles"]["get"]["parameters"]

    exclude_param = next(param for param in parameters if param["name"] == "exclude_summarized")

    assert exclude_param["in"] == "query"
    assert exclude_param["required"] is False
    assert exclude_param["schema"]["type"] == "boolean"
    assert exclude_param["schema"]["default"] is False


def test_summaries_endpoint_documents_fallback_query_param():
    schema = app.openapi()
    parameters = schema["paths"]["/api/summaries"]["get"]["parameters"]

    fallback_param = next(param for param in parameters if param["name"] == "fallback_to_latest")

    assert fallback_param["in"] == "query"
    assert fallback_param["required"] is False
    assert fallback_param["schema"]["type"] == "boolean"
    assert fallback_param["schema"]["default"] is False


def test_impact_metrics_endpoint_documents_date_and_fallback_query_params():
    schema = app.openapi()
    parameters = schema["paths"]["/api/impact-metrics"]["get"]["parameters"]

    date_param = next(param for param in parameters if param["name"] == "date")
    fallback_param = next(param for param in parameters if param["name"] == "fallback_to_latest")

    assert date_param["in"] == "query"
    assert date_param["required"] is False
    assert {"type": "string", "format": "date"} in date_param["schema"]["anyOf"]
    assert fallback_param["in"] == "query"
    assert fallback_param["required"] is False
    assert fallback_param["schema"]["type"] == "boolean"
    assert fallback_param["schema"]["default"] is True


def test_articles_today_falls_back_when_timezone_is_invalid():
    app_instance = SimpleNamespace(settings=SimpleNamespace(schedule_timezone="Invalid/Zone"))

    assert isinstance(_today_for_app(app_instance), date)
