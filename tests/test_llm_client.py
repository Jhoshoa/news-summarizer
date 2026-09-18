from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.llm.client import LLMProvider


def _fake_completion(content: str) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_gemini_provider_is_registered_with_openai_compatible_base_url():
    config = LLMProvider.PROVIDERS["gemini"]

    assert config["base_url"] == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert config["models"]["fast"] == "gemini-3.5-flash-lite"
    assert config["models"]["balanced"] == "gemini-3.5-flash-lite"
    assert config["models"]["quality"] == "gemini-3.6-flash"


def test_llm_provider_initializes_with_gemini():
    provider = LLMProvider(provider="gemini", api_key="fake-key")

    assert provider.provider == "gemini"
    assert provider.models["quality"] == "gemini-3.6-flash"


def test_kimi_provider_is_registered_with_openai_compatible_base_url():
    config = LLMProvider.PROVIDERS["kimi"]

    assert config["base_url"] == "https://api.moonshot.ai/v1"
    # Un solo modelo para las 3 calidades a proposito: kimi solo se usa como
    # ultimo respaldo de pago, no hace falta diferenciar velocidad/calidad
    # como con los proveedores gratuitos que reciben trafico normal.
    assert config["models"]["fast"] == "kimi-k2.6"
    assert config["models"]["balanced"] == "kimi-k2.6"
    assert config["models"]["quality"] == "kimi-k2.6"


def test_llm_provider_initializes_with_kimi():
    provider = LLMProvider(provider="kimi", api_key="fake-key")

    assert provider.provider == "kimi"
    assert provider.models["quality"] == "kimi-k2.6"


def test_kimi_gets_a_longer_timeout_than_the_shared_default():
    """Confirmado en vivo: un lote real de 8 noticias (el maximo de
    SUMMARY_CANDIDATES_EXTENDED_LIMIT) tarda 63.6s incluso con "thinking"
    desactivado, por encima del timeout de 45s compartido con groq/gemini/etc.
    Como kimi es siempre el ultimo proveedor del LLMRouter, cortarlo temprano
    solo tira la categoria a 0 resumenes sin ganar nada (no hay a quien
    pasarle la posta), asi que se ignora el timeout compartido que le pasa
    el router y se usa uno mas largo."""

    provider = LLMProvider(provider="kimi", api_key="fake-key", timeout=45.0)

    assert provider._client.timeout == 120.0


def test_other_providers_keep_the_shared_timeout():
    provider = LLMProvider(provider="groq", api_key="fake-key", timeout=45.0)

    assert provider._client.timeout == 45.0


@pytest.mark.asyncio
async def test_kimi_disables_thinking_and_forces_its_required_temperature():
    """kimi-k2.6 es un modelo "thinking" por defecto: gasta parte de
    max_tokens en un razonamiento interno oculto (reasoning_content) --
    confirmado en vivo, con thinking habilitado una llamada real de resumen
    tardo mas de 90s y termino en timeout, y una clasificacion simple tardo
    33-89s por el mismo motivo. Desactivar thinking (extra_body) la baja a
    ~2s sin gastar tokens en razonamiento. Con thinking desactivado el modelo
    exige otro temperature fijo -- confirmado en vivo: 400 "invalid
    temperature: only 0.6 is allowed for this model"."""

    provider = LLMProvider(provider="kimi", api_key="fake-key")
    mock_create = AsyncMock(return_value=_fake_completion("respuesta"))
    provider._client.chat.completions.create = mock_create

    result = await provider.chat("hola", quality="balanced", temperature=0.3, max_tokens=100)

    assert result == "respuesta"
    mock_create.assert_awaited_once_with(
        model="kimi-k2.6",
        messages=[{"role": "user", "content": "hola"}],
        temperature=0.6,
        max_tokens=100,
        extra_body={"thinking": {"type": "disabled"}},
    )


@pytest.mark.asyncio
async def test_other_providers_keep_the_requested_temperature_and_max_tokens():
    """Regresion: el ajuste especial para kimi no debe afectar a los demas
    proveedores, que si respetan la temperature/max_tokens pedidos."""

    provider = LLMProvider(provider="groq", api_key="fake-key")
    mock_create = AsyncMock(return_value=_fake_completion("respuesta"))
    provider._client.chat.completions.create = mock_create

    await provider.chat("hola", quality="balanced", temperature=0.3, max_tokens=100)

    mock_create.assert_awaited_once_with(
        model="qwen/qwen3.6-27b",
        messages=[{"role": "user", "content": "hola"}],
        temperature=0.3,
        max_tokens=100,
        extra_body=None,
    )
