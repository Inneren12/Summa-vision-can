"""Application configuration via Pydantic BaseSettings.

Settings are loaded from environment variables (and optionally a `.env` file).
Use the ``get_settings`` dependency in FastAPI route signatures to access
the parsed, validated configuration — never import a global instance.
"""

from functools import lru_cache
from typing import Literal

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

    # --- Audit (R18) ---
    audit_retention_days: int = 90

    # --- Security ---
    admin_api_key: str = ""  # Set via ADMIN_API_KEY env var

    # --- LLM / Gemini ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    daily_llm_budget: float = 5.00
    llm_cache_ttl_seconds: int = 86400  # 24 hours

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
