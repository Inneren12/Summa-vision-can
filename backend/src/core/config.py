"""Application configuration via Pydantic BaseSettings.

Settings are loaded from environment variables (and optionally a `.env` file).
Use the ``get_settings`` dependency in FastAPI route signatures to access
the parsed, validated configuration — never import a global instance.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the Summa Vision API.

    Attributes:
        app_name: Human-readable service name.
        debug: Enable debug-level logging and stack traces.
        cors_origins: Comma-separated list of allowed CORS origins.
            Defaults to ``"*"`` (allow all) for local development.
        storage_backend: Which storage implementation to use.
            ``"local"`` writes to disk (dev); ``"s3"`` uses AWS S3 (prod).
        s3_bucket: Name of the S3 bucket (required when *storage_backend*
            is ``"s3"``).
        s3_region: AWS region for the S3 bucket.
        s3_endpoint_url: Optional custom S3 endpoint (e.g. for LocalStack).
        s3_access_key_id: AWS access key ID (optional; falls back to
            standard AWS credential chain).
        s3_secret_access_key: AWS secret access key (optional; falls back
            to standard AWS credential chain).
        local_storage_dir: Filesystem directory used by
            ``LocalStorageManager``.
    """

    app_name: str = "Summa Vision API"
    debug: bool = False
    cors_origins: str = "*"
    environment: str = "development"

    # --- Application ---
    log_format: str = "console"  # "console" for dev, "json" for production

    # --- Database ---
    database_url: str = "postgresql+asyncpg://summa:devpassword@localhost:5432/summa"

    # --- Hard Caps (R15) ---
    max_preview_rows: int = 100
    max_chart_points: int = 500
    max_zip_size_mb: int = 100
    max_export_rows: int = 250_000
    max_token_uses: int = 5
    magic_token_ttl_hours: int = 48
    signed_url_ttl_minutes: int = 10
    max_job_retries: int = 3

    # --- Polars ---
    polars_max_threads: int = 2

    # --- Backup ---
    backup_s3_bucket: str = ""  # Set in production
    backup_retention_days: int = 30

    # --- Storage ---
    storage_backend: Literal["s3", "local"] = "local"  # "s3" or "local"
    s3_bucket: str = "summa-vision-dev"
    s3_endpoint_url: str = ""  # http://minio:9000 for dev, empty for AWS
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region: str = "us-east-1"
    # CDN_BASE_URL is the base URL for public lowres assets.
    # Gallery API constructs URLs as: f"{cdn_base_url}/{s3_key}"
    # where s3_key is the object key within the S3 bucket.
    #
    # Dev (MinIO direct): http://localhost:9000/summa-vision-dev
    # Prod (CloudFront):  https://cdn.summa.vision
    #
    # The key already contains the full path (e.g. "publications/42/v1/abc_lowres.png"),
    # so CDN_BASE_URL should NOT include a trailing path component.
    cdn_base_url: str = "http://localhost:9000/summa-vision-dev"
    local_storage_dir: str = "./data/local_storage"

    # --- Scheduler ---
    scheduler_db_url: str = "sqlite:///data/jobs.sqlite"
    scheduler_enabled: bool = True

    # --- Admin uploads ---
    # TTL for temp Parquet files written under ``temp/uploads/`` by
    # POST /api/v1/admin/graphics/generate-from-data.  Files older than
    # this are eligible for deletion by a (future) cleanup cron
    # (tracked as DEBT-021 until implemented).
    temp_upload_ttl_hours: int = Field(
        default=24,
        ge=1,
        description="TTL in hours for temp/uploads/ objects before cleanup.",
    )
    temp_upload_cleanup_interval_minutes: int = Field(
        default=60,
        ge=5,
        description="How often the temp uploads cleanup task runs.",
    )
    temp_cleanup_max_keys_per_cycle: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum expired objects scanned/deleted per prefix per cleanup cycle.",
    )
    temp_cleanup_prefixes: list[str] = Field(
        default_factory=lambda: ["temp/uploads/", "temp/"],
        description=(
            "S3 prefixes scanned by temp cleanup job (most-specific first)."
        ),
    )

    # --- Audit (R18) ---
    audit_retention_days: int = 90

    # --- Security ---
    admin_api_key: str = ""  # Set via ADMIN_API_KEY env var
    turnstile_secret_key: str = ""  # Set via TURNSTILE_SECRET_KEY env var

    # --- Public Site ---
    public_site_url: str = "http://localhost:3000"  # Prod: https://summa.vision

    # --- Slack ---
    SLACK_WEBHOOK_URL: str = ""  # If empty → Slack notifications silently disabled

    # --- ESP (Beehiiv) ---
    BEEHIIV_API_KEY: str = ""  # If empty → ESP sync silently disabled
    BEEHIIV_PUBLICATION_ID: str = ""

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        """Fail fast at startup if critical secrets are missing."""
        errors: list[str] = []

        # Always required
        if not self.database_url:
            errors.append("DATABASE_URL is required")
        if not self.admin_api_key:
            errors.append("ADMIN_API_KEY is required")
        if not self.s3_bucket:
            errors.append("S3_BUCKET is required")

        # Required for public site features (Étape D)
        # These can be empty during dev but must be set in production
        if self.environment == "production":
            if not self.cdn_base_url:
                errors.append("CDN_BASE_URL is required in production")
            if not self.public_site_url:
                errors.append("PUBLIC_SITE_URL is required in production")
            if not self.turnstile_secret_key:
                errors.append("TURNSTILE_SECRET_KEY is required in production")

        if errors:
            raise ValueError(
                "Missing required configuration:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (singleton per process).

    This function is designed to be used as a **FastAPI dependency**::

        @app.get("/example")
        async def example(settings: Settings = Depends(get_settings)):
            ...

    The ``@lru_cache`` decorator ensures the ``.env`` file is read only
    once, making repeated dependency resolution essentially free.
    """
    return Settings()
