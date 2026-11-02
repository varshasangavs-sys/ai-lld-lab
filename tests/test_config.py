import pytest

from ai_lld_lab.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_defaults():
    settings = Settings()
    assert settings.app_name == "ai-lld-lab"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_get_settings_returns_same_cached_instance():
    first = get_settings()
    second = get_settings()
    assert first is second


def test_get_settings_reads_env_vars(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ENVIRONMENT", "test")

    settings = get_settings()

    assert settings.log_level == "DEBUG"
    assert settings.environment == "test"


def test_cache_clear_picks_up_new_env(monkeypatch):
    monkeypatch.setenv("APP_NAME", "first-name")
    first = get_settings()
    assert first.app_name == "first-name"

    get_settings.cache_clear()
    monkeypatch.setenv("APP_NAME", "second-name")
    second = get_settings()

    assert second.app_name == "second-name"
    assert first is not second
