"""Tests for the shared call_db() helper used across src/api/*.py routers to
turn a mid-request DB failure into a clean 503 instead of a raw 500 (see
src/api/preferences.py's original fix for the Sentry-reported
[WinError 121] crash -- this is the same helper, now shared by every
router that touches app_instance.db)."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.db_errors import call_db


@pytest.mark.asyncio
async def test_call_db_returns_the_result_on_success():
    result = await call_db(AsyncMock(return_value={"ok": True})(), action="test")

    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_call_db_turns_an_unexpected_exception_into_a_503():
    async def flaky():
        raise OSError("[WinError 121] The semaphore timeout period has expired")

    with pytest.raises(HTTPException) as exc_info:
        await call_db(flaky(), action="test_action")

    assert exc_info.value.status_code == 503
    assert "base de datos" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_call_db_reports_the_original_exception_to_sentry(monkeypatch):
    captured = []
    monkeypatch.setattr(
        "src.api.db_errors.sentry_sdk.capture_exception", lambda e: captured.append(e)
    )

    async def flaky():
        raise ConnectionResetError("boom")

    with pytest.raises(HTTPException):
        await call_db(flaky(), action="test_action")

    assert len(captured) == 1
    assert isinstance(captured[0], ConnectionResetError)


@pytest.mark.asyncio
async def test_call_db_lets_a_deliberate_http_exception_pass_through_unchanged():
    """A 404 raised by application logic inside the wrapped call (e.g. 'not
    found') must not get swallowed and rewritten into a generic 503."""

    async def not_found():
        raise HTTPException(status_code=404, detail="Historia no encontrada")

    with pytest.raises(HTTPException) as exc_info:
        await call_db(not_found(), action="test_action")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Historia no encontrada"
