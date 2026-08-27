from src.llm.client import LLMProvider


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
