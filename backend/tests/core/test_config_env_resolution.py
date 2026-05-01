"""Phase 2 deploy: verify Settings.environment resolves from both env var names."""

import pytest

from src.core.config import Settings


COMMON_REQUIRED = {
    "DATABASE_URL": "postgresql+asyncpg://localhost/db",
    "ADMIN_API_KEY": "x",
    "S3_BUCKET": "summa-dev",
    "CDN_BASE_URL": "https://cdn.summa.vision",
    "PUBLIC_SITE_URL": "https://summa.vision",
    "TURNSTILE_SECRET_KEY": "turnstile-secret",
}


def _set_required(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in COMMON_REQUIRED.items():
        monkeypatch.setenv(k, v)


def test_environment_reads_from_environment_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("APP_ENV", raising=False)
    _set_required(monkeypatch)

    s = Settings(_env_file=None)
    assert s.environment == "production"


def test_environment_reads_from_app_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    _set_required(monkeypatch)

    s = Settings(_env_file=None)
    assert s.environment == "production"


def test_production_requires_prod_secrets_when_resolved_from_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    _set_required(monkeypatch)
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "")

    with pytest.raises(ValueError, match="TURNSTILE_SECRET_KEY"):
        Settings(_env_file=None)


def test_dev_does_not_enforce_prod_validations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("DATABASE_URL", COMMON_REQUIRED["DATABASE_URL"])
    monkeypatch.setenv("ADMIN_API_KEY", COMMON_REQUIRED["ADMIN_API_KEY"])
    monkeypatch.setenv("S3_BUCKET", COMMON_REQUIRED["S3_BUCKET"])
    monkeypatch.setenv("CDN_BASE_URL", "")
    monkeypatch.setenv("PUBLIC_SITE_URL", "")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "")

    s = Settings(_env_file=None)
    assert s.environment == "development"
