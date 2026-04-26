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

    status_code_value = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "PUBLICATION_UPDATE_PAYLOAD_INVALID"
    message = "The submitted changes are invalid."


class PublicationInternalSerializationError(PublicationApiError):
    """Repository serialization invariant violated (e.g., unsupported type in JSON column)."""

    status_code_value = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "PUBLICATION_INTERNAL_SERIALIZATION_ERROR"
    message = "Could not save this publication due to a server data format issue."
