"""Unified exception hierarchy for the Summa Vision platform.

Every domain-specific error inherits from :class:`SummaVisionError`, which
carries a machine-readable ``error_code``, a human-readable ``message``, and
an optional ``context`` dict for structured metadata.  This ensures that
**all** exceptions surfaced to the API layer share a consistent shape and
can be serialized into the standard JSON envelope by the global error handler.

Usage::

    raise DataSourceError(
        message="StatCan WDS returned HTTP 503",
        error_code="DATASOURCE_UNAVAILABLE",
        context={"url": url, "status_code": 503},
    )
"""

from __future__ import annotations


class SummaVisionError(Exception):
    """Base exception for every Summa Vision domain error.

    Attributes:
        message:  Human-readable description of the error.
        error_code:  Machine-readable error code (e.g. ``"VALIDATION_FAILED"``).
        context:  Arbitrary key/value pairs that provide debugging context.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        error_code: str = "SUMMA_VISION_ERROR",
        context: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.context: dict[str, object] = context or {}
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Domain-specific subclasses
# ---------------------------------------------------------------------------


class WorkbenchError(SummaVisionError):
    """Raised when a data workbench transform fails.

    Examples: missing merge keys, duplicate key violation,
    invalid frequency/method, empty DataFrame input.
    """

    def __init__(
        self,
        message: str = "Workbench error",
        error_code: str = "WORKBENCH_ERROR",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, context=context)


class DataSourceError(SummaVisionError):
    """Raised when an external data source (StatCan, CMHC, etc.) fails.

    Covers HTTP errors, timeouts, unexpected response formats, and
    maintenance-window violations.
    """

    def __init__(
        self,
        message: str = "Data source error",
        error_code: str = "DATASOURCE_ERROR",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, context=context)


class AIServiceError(SummaVisionError):
    """Raised when the LLM Gate (Gemini) or any AI service call fails.

    Covers API quota exhaustion, malformed LLM responses, and prompt
    validation failures.
    """

    def __init__(
        self,
        message: str = "AI service error",
        error_code: str = "AI_SERVICE_ERROR",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, context=context)


class StorageError(SummaVisionError):
    """Raised when persistence operations fail.

    Covers database write failures, S3/GCS upload errors, and
    file-system permission issues.
    """

    def __init__(
        self,
        message: str = "Storage error",
        error_code: str = "STORAGE_ERROR",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, context=context)


class ValidationError(SummaVisionError):
    """Raised when input data fails business-rule validation.

    This is **not** the same as Pydantic's ``ValidationError``; it is used
    for domain-level validation (e.g. "virality score out of range").
    """

    def __init__(
        self,
        message: str = "Validation error",
        error_code: str = "VALIDATION_ERROR",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, context=context)


class AuthError(SummaVisionError):
    """Raised when authentication or authorisation checks fail.

    Covers missing/expired tokens, insufficient permissions, and
    API-key validation failures.
    """

    def __init__(
        self,
        message: str = "Authentication error",
        error_code: str = "AUTH_ERROR",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, context=context)


class NotFoundError(SummaVisionError):
    """Raised when a requested entity does not exist."""
    def __init__(
        self,
        message: str = "Not found",
        error_code: str = "NOT_FOUND",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, context=context)


class ConflictError(SummaVisionError):
    """Raised when an operation conflicts with current resource state.
    Covers business-rule violations such as retrying a non-failed job
    or violating a dedupe constraint.
    """
    def __init__(
        self,
        message: str = "Conflict",
        error_code: str = "CONFLICT",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, context=context)


class ESPPermanentError(SummaVisionError):
    """Raised when the ESP (e.g. Beehiiv) returns a 4xx client error.
    These errors indicate a permanent failure that should NOT be retried
    (e.g. invalid email, duplicate subscriber rejection).
    """
    def __init__(
        self,
        status_code: int,
        detail: str = "ESP permanent error",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=detail,
            error_code="ESP_PERMANENT_ERROR",
            context={"status_code": status_code, **(context or {})},
        )
        self.status_code = status_code


class ESPTransientError(SummaVisionError):
    """Raised when the ESP returns a 5xx server error or times out.
    These errors are transient and the operation should be retried
    with exponential backoff.
    """
    def __init__(
        self,
        status_code: int,
        detail: str = "ESP transient error",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=detail,
            error_code="ESP_TRANSIENT_ERROR",
            context={"status_code": status_code, **(context or {})},
        )
        self.status_code = status_code