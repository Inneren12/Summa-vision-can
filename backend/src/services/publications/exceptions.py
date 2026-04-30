"""Publication API exception classes with structured error_code contract.

These exceptions inherit from FastAPI's HTTPException and serialize their
error_code into the `detail` payload as {error_code, message[, details]}.

See docs/debt-030-recon.md §5 for vocabulary.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class PublicationApiError(HTTPException):
    """Base class. Subclasses set status_code_value, error_code, message."""

    status_code_value: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "PUBLICATION_UNKNOWN_ERROR"
    message: str = "Publication action failed."

    def __init__(self, *, details: dict[str, Any] | None = None) -> None:
        detail_payload: dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if details is not None:
            detail_payload["details"] = details
        super().__init__(
            status_code=self.status_code_value,
            detail=detail_payload,
        )


class PublicationNotFoundError(PublicationApiError):
    """Requested publication_id does not exist."""

    status_code_value = status.HTTP_404_NOT_FOUND
    error_code = "PUBLICATION_NOT_FOUND"
    message = "Publication not found."


class PublicationUpdatePayloadInvalidError(PublicationApiError):
    """PATCH body failed Pydantic validation. `details.validation_errors` carries field info."""

    status_code_value = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "PUBLICATION_UPDATE_PAYLOAD_INVALID"
    message = "The submitted changes are invalid."


class PublicationInternalSerializationError(PublicationApiError):
    """Repository serialization invariant violated (e.g., unsupported type in JSON column)."""

    status_code_value = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "PUBLICATION_INTERNAL_SERIALIZATION_ERROR"
    message = "Could not save this publication due to a server data format issue."


class PublicationCloneNotAllowedError(PublicationApiError):
    """Clone attempted for a publication that is not in PUBLISHED status."""

    status_code_value = status.HTTP_409_CONFLICT
    error_code = "PUBLICATION_CLONE_NOT_ALLOWED"
    message = "Only published publications can be cloned."

    def __init__(self, *, publication_id: int, current_status: str) -> None:
        super().__init__(details={
            "publication_id": publication_id,
            "current_status": current_status,
        })


class PublicationPreconditionFailedError(PublicationApiError):
    """Raised when If-Match header on PATCH does not match server ETag.

    Surfaces as HTTP 412 with envelope::

        {"detail": {
            "error_code": "PRECONDITION_FAILED",
            "message": "<EN message>",
            "details": {"server_etag": str, "client_etag": str}
        }}

    error_code per docs/architecture/ARCHITECTURE_INVARIANTS.md §3.
    """

    status_code_value = status.HTTP_412_PRECONDITION_FAILED
    error_code = "PRECONDITION_FAILED"
    message = "The publication has been modified since you loaded it."

    def __init__(self, *, server_etag: str, client_etag: str) -> None:
        super().__init__(details={
            "server_etag": server_etag,
            "client_etag": client_etag,
        })


class PublicationSlugGenerationError(PublicationApiError):
    """Slug body empty/too short after slugification."""

    status_code_value = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "PUBLICATION_SLUG_GENERATION_FAILED"
    message = "headline produces empty/short slug body (min=3 chars)."

    def __init__(self, *, headline: str) -> None:
        super().__init__(details={"headline": headline})


class PublicationSlugCollisionError(PublicationApiError):
    """Slug suffix space -2..-99 exhausted (98 attempts)."""

    status_code_value = status.HTTP_409_CONFLICT
    error_code = "PUBLICATION_SLUG_COLLISION_EXHAUSTED"
    message = "Slug collision suffix range exhausted; rename headline."

    def __init__(self, *, base_slug: str, attempts: int) -> None:
        super().__init__(details={"base_slug": base_slug, "attempts": attempts})
