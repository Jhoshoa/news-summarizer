from src.config.settings import Settings
from src.db.repository import DEFAULT_CATEGORIES


def test_default_categories_default_matches_the_single_source_of_truth(monkeypatch):
    """Regression test: settings.py used to hardcode its own 6-item category
    string (missing "general"), independent from DEFAULT_CATEGORIES in
    repository.py. It should now be derived from that dict directly."""

    monkeypatch.delenv("DEFAULT_CATEGORIES", raising=False)

    settings = Settings(_env_file=None)

    assert settings.categories_list == list(DEFAULT_CATEGORIES.keys())
    assert "general" in settings.categories_list
    assert "policiales" in settings.categories_list


def test_default_categories_env_override_still_takes_precedence(monkeypatch):
    monkeypatch.setenv("DEFAULT_CATEGORIES", "economia,deportes")

    settings = Settings(_env_file=None)

    assert settings.categories_list == ["economia", "deportes"]


def test_llm_providers_list_includes_gemini_when_key_is_set(monkeypatch):
    monkeypatch.delenv("LLM_FALLBACK_ORDER", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.delenv("GITHUB_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.llm_providers_list == [
        {"provider": "groq", "api_key": "groq-key"},
        {"provider": "gemini", "api_key": "gemini-key"},
    ]


def test_llm_providers_list_skips_gemini_without_a_key(monkeypatch):
    monkeypatch.delenv("LLM_FALLBACK_ORDER", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.llm_providers_list == [{"provider": "groq", "api_key": "groq-key"}]
