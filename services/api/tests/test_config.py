from app.core.config import get_settings


def test_settings_read_server_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://example/test")
    monkeypatch.setenv("ARK_API_KEY", "server-only-key")
    monkeypatch.setenv("ARK_MODEL", "doubao-test-model")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_url == "postgresql+psycopg://example/test"
    assert settings.ark_api_key.get_secret_value() == "server-only-key"
    assert settings.ark_model == "doubao-test-model"
    get_settings.cache_clear()
