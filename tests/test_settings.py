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
