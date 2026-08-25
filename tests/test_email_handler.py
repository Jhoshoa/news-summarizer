from email.message import EmailMessage
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.distributors.email_handler import EmailHandler


def _settings(**overrides):
    base = {
        "email_enabled": True,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "sender@example.com",
        "smtp_password": "app-password",
        "smtp_from_email": "sender@example.com",
        "smtp_from_name": "EcoBrief Bolivia",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_email_handler_requires_full_smtp_configuration():
    handler = EmailHandler(settings=_settings(smtp_password=None))

    assert handler.is_configured is False


def test_email_handler_builds_plain_text_message():
    handler = EmailHandler(settings=_settings())

    message = handler._build_message(
        "reader@example.com",
        "EcoBrief Bolivia - Brief del dia",
        "Contenido",
    )

    assert isinstance(message, EmailMessage)
    assert message["Subject"] == "EcoBrief Bolivia - Brief del dia"
    assert message["From"] == "EcoBrief Bolivia <sender@example.com>"
    assert message["To"] == "reader@example.com"
    assert message.get_content().strip() == "Contenido"


def test_email_handler_builds_multipart_html_message():
    handler = EmailHandler(settings=_settings())

    message = handler._build_message(
        "reader@example.com",
        "EcoBrief Bolivia - Brief del dia",
        "Contenido",
        html_body="<p>Contenido <a href=\"https://example.com\">Link</a></p>",
    )

    assert message.is_multipart()
    assert message.get_body(preferencelist=("plain",)).get_content().strip() == "Contenido"
    html_part = message.get_body(preferencelist=("html",)).get_content()
    assert '<a href="https://example.com">Link</a>' in html_part


@pytest.mark.asyncio
async def test_email_handler_sends_with_configured_smtp(monkeypatch):
    sent_messages = []
    handler = EmailHandler(settings=_settings())

    def fake_send(message):
        sent_messages.append(message)

    monkeypatch.setattr(handler, "_send_sync", fake_send)

    result = await handler.send_message("reader@example.com", "Asunto", "Contenido")

    assert result is True
    assert sent_messages[0]["To"] == "reader@example.com"


@pytest.mark.asyncio
async def test_email_handler_does_not_send_when_disabled(monkeypatch):
    handler = EmailHandler(settings=_settings(email_enabled=False))

    def fail_send(message):
        raise AssertionError("SMTP should not be called")

    monkeypatch.setattr(handler, "_send_sync", fail_send)

    result = await handler.send_message("reader@example.com", "Asunto", "Contenido")

    assert result is False


def _fake_smtp_context_manager():
    """SMTP/SMTP_SSL se usan como `with SMTP(...) as smtp:` — el mock debe
    soportar el protocolo de context manager, no solo ser llamable."""

    instance = MagicMock()
    context = MagicMock()
    context.__enter__ = MagicMock(return_value=instance)
    context.__exit__ = MagicMock(return_value=False)
    return context, instance


def test_send_sync_uses_starttls_for_non_465_ports():
    handler = EmailHandler(settings=_settings(smtp_port=587))
    message = EmailMessage()

    smtp_context, smtp_instance = _fake_smtp_context_manager()
    ssl_context, ssl_instance = _fake_smtp_context_manager()

    with (
        patch("smtplib.SMTP", return_value=smtp_context) as smtp_cls,
        patch("smtplib.SMTP_SSL", return_value=ssl_context) as ssl_cls,
    ):
        handler._send_sync(message)

    smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=20)
    ssl_cls.assert_not_called()
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("sender@example.com", "app-password")
    smtp_instance.send_message.assert_called_once_with(message)


def test_send_sync_uses_implicit_ssl_for_port_465():
    handler = EmailHandler(settings=_settings(smtp_port=465))
    message = EmailMessage()

    smtp_context, smtp_instance = _fake_smtp_context_manager()
    ssl_context, ssl_instance = _fake_smtp_context_manager()

    with (
        patch("smtplib.SMTP", return_value=smtp_context) as smtp_cls,
        patch("smtplib.SMTP_SSL", return_value=ssl_context) as ssl_cls,
    ):
        handler._send_sync(message)

    ssl_cls.assert_called_once_with("smtp.gmail.com", 465, timeout=20)
    smtp_cls.assert_not_called()
    ssl_instance.starttls.assert_not_called()  # TLS ya es implicito en SMTP_SSL
    ssl_instance.login.assert_called_once_with("sender@example.com", "app-password")
    ssl_instance.send_message.assert_called_once_with(message)
