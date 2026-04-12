"""Tests for startup validation of required secrets (DEBT-008)."""

import pytest

from src.core.config import Settings


class TestSettingsRequiredSecrets:
    """Validator must reject missing critical secrets at startup."""

    def test_missing_database_url_raises(self) -> None:
        with pytest.raises(ValueError, match="DATABASE_URL is required"):
            Settings(
                _env_file=None,
                database_url="",
                admin_api_key="x",
                s3_bucket="x",
            )

    def test_missing_admin_api_key_raises(self) -> None:
        with pytest.raises(ValueError, match="ADMIN_API_KEY is required"):
            Settings(
                _env_file=None,
                database_url="postgresql+asyncpg://localhost/db",
                admin_api_key="",
                s3_bucket="x",
            )

    def test_missing_s3_bucket_raises(self) -> None:
        with pytest.raises(ValueError, match="S3_BUCKET is required"):
            Settings(
                _env_file=None,
                database_url="postgresql+asyncpg://localhost/db",
                admin_api_key="x",
                s3_bucket="",
            )

    def test_multiple_missing_secrets_lists_all(self) -> None:
        with pytest.raises(ValueError, match="DATABASE_URL is required") as exc_info:
            Settings(
                _env_file=None,
                database_url="",
                admin_api_key="",
                s3_bucket="",
            )
        msg = str(exc_info.value)
        assert "ADMIN_API_KEY is required" in msg
        assert "S3_BUCKET is required" in msg


class TestSettingsProductionSecrets:
    """Production environment requires additional secrets."""

    def test_production_requires_cdn_base_url(self) -> None:
        with pytest.raises(ValueError, match="CDN_BASE_URL is required in production"):
            Settings(
                _env_file=None,
                database_url="postgresql+asyncpg://localhost/db",
                admin_api_key="x",
                s3_bucket="x",
                environment="production",
                cdn_base_url="",
                public_site_url="https://summa.vision",
                turnstile_secret_key="secret",
            )

    def test_production_requires_public_site_url(self) -> None:
        with pytest.raises(ValueError, match="PUBLIC_SITE_URL is required in production"):
            Settings(
                _env_file=None,
                database_url="postgresql+asyncpg://localhost/db",
                admin_api_key="x",
                s3_bucket="x",
                environment="production",
                cdn_base_url="https://cdn.summa.vision",
                public_site_url="",
                turnstile_secret_key="secret",
            )

    def test_production_requires_turnstile_secret(self) -> None:
        with pytest.raises(ValueError, match="TURNSTILE_SECRET_KEY is required in production"):
            Settings(
                _env_file=None,
                database_url="postgresql+asyncpg://localhost/db",
                admin_api_key="x",
                s3_bucket="x",
                environment="production",
                cdn_base_url="https://cdn.summa.vision",
                public_site_url="https://summa.vision",
                turnstile_secret_key="",
            )

    def test_dev_allows_empty_cdn(self) -> None:
        """Development environment should NOT require CDN/public-site secrets."""
        s = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://localhost/db",
            admin_api_key="x",
            s3_bucket="x",
            environment="development",
            cdn_base_url="",
            public_site_url="",
            turnstile_secret_key="",
        )
        assert s.environment == "development"

    def test_production_valid_config_passes(self) -> None:
        """Fully-populated production config must not raise."""
        s = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://localhost/db",
            admin_api_key="prod-secret",
            s3_bucket="summa-prod",
            environment="production",
            cdn_base_url="https://cdn.summa.vision",
            public_site_url="https://summa.vision",
            turnstile_secret_key="cf-secret",
        )
        assert s.environment == "production"
