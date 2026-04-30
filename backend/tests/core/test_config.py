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


class TestEnvIgnoreEmpty:
    """Tests for env_ignore_empty=True semantics in Settings.model_config.

    Without env_ignore_empty=True (the prior behavior), an empty env var would
    override the Pydantic Python default with empty string. With it set, an
    empty env var is treated as if the var is unset, so the Python default
    applies. Tests in this class verify that semantic.
    """

    REQUIRED_BASE_ENV = {
        "DATABASE_URL": "postgresql+asyncpg://x:y@z:5432/w",
        "ADMIN_API_KEY": "test-admin-key",
        "S3_BUCKET": "test-bucket",
    }

    def _set_required(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for k, v in self.REQUIRED_BASE_ENV.items():
            monkeypatch.setenv(k, v)

    def test_empty_env_falls_back_to_python_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LOG_FORMAT='' -> defaults to 'console' (Settings.log_format Python default)."""
        self._set_required(monkeypatch)
        monkeypatch.setenv("LOG_FORMAT", "")
        s = Settings(_env_file=None)
        assert s.log_format == "console"

    def test_unset_env_uses_python_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LOG_FORMAT not set -> defaults to 'console' (regression check)."""
        self._set_required(monkeypatch)
        monkeypatch.delenv("LOG_FORMAT", raising=False)
        s = Settings(_env_file=None)
        assert s.log_format == "console"

    def test_explicit_non_empty_env_wins(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LOG_FORMAT='json' -> 'json' (regression check, host value wins)."""
        self._set_required(monkeypatch)
        monkeypatch.setenv("LOG_FORMAT", "json")
        s = Settings(_env_file=None)
        assert s.log_format == "json"

    def test_empty_storage_backend_falls_back_to_local(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """STORAGE_BACKEND='' -> 'local' (Literal field — used to raise, now falls back)."""
        self._set_required(monkeypatch)
        monkeypatch.setenv("STORAGE_BACKEND", "")
        s = Settings(_env_file=None)
        assert s.storage_backend == "local"

    def test_empty_required_secret_in_production_still_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TURNSTILE_SECRET_KEY='' in production fails validation (Python default also '')."""
        self._set_required(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "production")
        # Provide other required-in-prod fields with non-empty values so we
        # isolate TURNSTILE_SECRET_KEY as the failure cause.
        monkeypatch.setenv("CDN_BASE_URL", "https://cdn.example.com")
        monkeypatch.setenv("PUBLIC_SITE_URL", "https://example.com")
        monkeypatch.setenv("TURNSTILE_SECRET_KEY", "")
        with pytest.raises(ValueError, match="TURNSTILE_SECRET_KEY is required"):
            Settings(_env_file=None)

    def test_empty_database_url_falls_back_to_python_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DATABASE_URL='' -> uses Python default DSN, validator passes.

        Behavior change from prior env_ignore_empty=False: empty env used to
        wipe Python default -> validator failed. Now empty is treated as unset
        -> Python default applies -> validator sees non-empty value.
        """
        monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
        monkeypatch.setenv("S3_BUCKET", "test-bucket")
        monkeypatch.setenv("DATABASE_URL", "")
        s = Settings(_env_file=None)
        # Python default contains 'postgresql+asyncpg://' prefix
        assert s.database_url.startswith("postgresql+asyncpg://")

    def test_empty_cdn_base_url_in_production_uses_python_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CDN_BASE_URL='' in production -> Python default applies, validator passes.

        Behavior change worth flagging: previously empty would fail prod validator,
        now Python default localhost URL applies. Per PR-D recon Section 7, this
        is SAFE because empty CDN is an accidental dev-state, not an intentional
        prod misconfiguration. Operators are expected to set CDN_BASE_URL
        explicitly in production deploys.
        """
        self._set_required(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("PUBLIC_SITE_URL", "https://example.com")
        monkeypatch.setenv("TURNSTILE_SECRET_KEY", "test-turnstile")
        monkeypatch.setenv("CDN_BASE_URL", "")
        s = Settings(_env_file=None)
        assert s.cdn_base_url == "http://localhost:9000/summa-vision-dev"
