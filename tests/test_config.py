import pytest

from app.config import ConfigError, validate_config


def test_missing_configuration_lists_every_variable(monkeypatch):
    for name in ("GEMINI_API_KEY", "RESEND_API_KEY", "DIGEST_RECIPIENT_EMAIL", "NEON_DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ConfigError) as excinfo:
        validate_config()

    message = str(excinfo.value)
    for name in ("GEMINI_API_KEY", "RESEND_API_KEY", "DIGEST_RECIPIENT_EMAIL", "NEON_DATABASE_URL"):
        assert name in message


def test_valid_configuration_passes(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("RESEND_API_KEY", "r")
    monkeypatch.setenv("DIGEST_RECIPIENT_EMAIL", "reader@example.com")
    monkeypatch.setenv("NEON_DATABASE_URL", "postgresql+psycopg2://user:pass@host/db")

    validate_config()
