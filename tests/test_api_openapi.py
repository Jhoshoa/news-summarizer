from src.main import app


def test_economic_indicators_endpoint_documents_date_query_param():
    schema = app.openapi()
    parameters = schema["paths"]["/api/economic-indicators"]["get"]["parameters"]

    date_param = next(param for param in parameters if param["name"] == "date")

    assert date_param["in"] == "query"
    assert date_param["required"] is False
    assert {"type": "string", "format": "date"} in date_param["schema"]["anyOf"]
