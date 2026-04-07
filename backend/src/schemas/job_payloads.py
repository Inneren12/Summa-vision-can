"""Typed payload models for persistent jobs.

Each job_type has a corresponding Pydantic model that validates its
payload. All payloads include ``schema_version`` so that backward
compatibility can be verified after deploys (see Deploy Compatibility
Rules in ROADMAP_v8_FINAL.md).

Usage:
    payload = CubeFetchPayload(product_id="14-10-0127")
    job, _ = await repo.enqueue("cube_fetch", payload)

    # Later, in runner:
    typed = parse_payload(job)  # returns CubeFetchPayload
"""

from __future__ import annotations

from pydantic import BaseModel

from src.core.exceptions import SummaVisionError


class IncompatiblePayloadError(SummaVisionError):
    """Raised when a job payload has an unsupported schema_version."""

    def __init__(self, job_type: str, version: int) -> None:
        super().__init__(
            message=f"Incompatible payload schema v{version} for job type '{job_type}'",
            error_code="INCOMPATIBLE_PAYLOAD_VERSION",
            context={"job_type": job_type, "schema_version": version},
        )


class UnknownJobTypeError(SummaVisionError):
    """Raised when a job_type has no registered payload model."""

    def __init__(self, job_type: str) -> None:
        super().__init__(
            message=f"Unknown job type: '{job_type}'",
            error_code="UNKNOWN_JOB_TYPE",
            context={"job_type": job_type},
        )


# ---------------------------------------------------------------------------
# Payload models — one per job_type
# ---------------------------------------------------------------------------

class CatalogSyncPayload(BaseModel):
    """Payload for full StatCan catalog synchronization."""
    schema_version: int = 1


class CubeFetchPayload(BaseModel):
    """Payload for fetching data vectors for a single cube."""
    schema_version: int = 1
    product_id: str


class TransformPayload(BaseModel):
    """Payload for applying Workbench transforms to stored data."""
    schema_version: int = 1
    source_keys: list[str]
    operations: list[dict[str, object]]
    output_key: str | None = None


class GraphicsGeneratePayload(BaseModel):
    """Payload for generating a publication graphic."""
    schema_version: int = 1
    data_key: str
    chart_type: str
    title: str
    size: tuple[int, int] = (1200, 900)
    category: str = "housing"


# ---------------------------------------------------------------------------
# Registry + dispatcher
# ---------------------------------------------------------------------------

CURRENT_SCHEMA_VERSION = 1

PAYLOAD_REGISTRY: dict[str, type[BaseModel]] = {
    "catalog_sync": CatalogSyncPayload,
    "cube_fetch": CubeFetchPayload,
    "transform": TransformPayload,
    "graphics_generate": GraphicsGeneratePayload,
}


def parse_payload(job_type: str, payload_json: str) -> BaseModel:
    """Validate and deserialize a job payload.

    NOTE: Roadmap specifies ``parse_payload(job) -> BaseModel``.
    This implementation accepts (job_type, payload_json) directly
    for flexibility — callers may not always have the full Job object
    (e.g. in tests, in API validation before enqueue).
    The runner calls: ``parse_payload(job.job_type, job.payload_json)``.

    Args:
        job_type: The job's type identifier.
        payload_json: Raw JSON string from ``Job.payload_json``.

    Returns:
        A validated Pydantic model instance.

    Raises:
        UnknownJobTypeError: If ``job_type`` is not in the registry.
        IncompatiblePayloadError: If ``schema_version`` is not supported.
    """
    cls = PAYLOAD_REGISTRY.get(job_type)
    if cls is None:
        raise UnknownJobTypeError(job_type)

    parsed = cls.model_validate_json(payload_json)

    if parsed.schema_version != CURRENT_SCHEMA_VERSION:
        raise IncompatiblePayloadError(job_type, parsed.schema_version)

    return parsed