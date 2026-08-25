from types import SimpleNamespace
from unittest.mock import patch

from src.main import NewsSummarizerApp


def _make_app(sentry_dsn=None, environment="production"):
    settings = SimpleNamespace(sentry_dsn=sentry_dsn, environment=environment)
    return NewsSummarizerApp(settings)


def test_init_sentry_noop_without_dsn():
    app = _make_app(sentry_dsn=None)
    with patch("sentry_sdk.init") as mock_init:
        app._init_sentry()
    mock_init.assert_not_called()


def test_init_sentry_initializes_with_dsn():
    app = _make_app(sentry_dsn="https://fake@sentry.example/1", environment="production")
    with patch("sentry_sdk.init") as mock_init:
        app._init_sentry()
    mock_init.assert_called_once_with(
        dsn="https://fake@sentry.example/1",
        environment="production",
        traces_sample_rate=0.1,
    )


def test_init_sentry_does_not_raise_on_invalid_configuration():
    app = _make_app(sentry_dsn="not-a-real-dsn")
    with patch("sentry_sdk.init", side_effect=RuntimeError("bad dsn")):
        app._init_sentry()  # no debe lanzar
