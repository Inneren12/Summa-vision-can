"""Global FastAPI exception handler for :class:`SummaVisionError`.

This module registers a single handler that intercepts every exception in the
``SummaVisionError`` hierarchy, logs the error together with its structured
context via *structlog*, and returns a deterministic JSON envelope to the
client.

Usage::

    from fastapi import FastAPI, status
    from src.core.error_handler import register_exception_handlers

    app = FastAPI()
    register_exception_handlers(app)
"""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

from fastapi import FastAPI, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

from src.core.exceptions import SummaVisionError
from src.core.logging import get_logger
from src.services.publications.exceptions import (
    PublicationPreconditionFailedError,
)

if TYPE_CHECKING:
    pass

logger = get_logger(service="error_handler")

# Mapping from error_code prefixes to HTTP status codes.
_ERROR_CODE_TO_STATUS: dict[str, int] = {
    "AUTH_ERROR": 401,
    "VALIDATION_ERROR": 422,
    "DATASOURCE_ERROR": 502,
    "AI_SERVICE_ERROR": 502,
    "STORAGE_ERROR": 500,
}

_DEFAULT_STATUS_CODE = 500


def _status_code_for(error_code: str) -> int:
    """Resolve an HTTP status code from the exception's ``error_code``."""
    return _ERROR_CODE_TO_STATUS.get(error_code, _DEFAULT_STATUS_CODE)


def format_error_envelope(
    *,
    error_code: str,
    message: str,
    context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the canonical nested error envelope.

    Used by AuthMiddleware (DEBT-034) and any future caller that needs to
    emit the canonical envelope from outside the FastAPI exception-handler
    pipeline (e.g. ASGI middleware where exceptions don't always route
    through registered handlers).

    Returns a dict matching the publication-handler nested shape:

        {"detail": {"error_code": "<code>", "message": "<msg>", "context": {}}}

    NOTE: This helper does NOT yet replace ``_summa_vision_exception_handler``
    which still emits the legacy flat envelope. That migration is tracked
    by DEBT-048.
    """
    return {
        "detail": {
            "error_code": error_code,
            "message": message,
            "context": context or {},
        },
    }


async def _summa_vision_exception_handler(
    request: Request,
    exc: SummaVisionError,
) -> JSONResponse:
    """Handle any :class:`SummaVisionError` raised during request processing.

    The handler:
    1. Logs the exception with *structlog* including full traceback and context.
    2. Returns a standardised JSON body::

        {
            "error_code": "DATASOURCE_ERROR",
            "message": "StatCan WDS returned HTTP 503",
            "detail": {"url": "...", "status_code": 503}
        }
    """
    logger.error(
        exc.message,
        error_code=exc.error_code,
        context=exc.context,
        service_name="summa_vision",
        traceback=traceback.format_exception(type(exc), exc, exc.__traceback__),
    )

    return JSONResponse(
        status_code=_status_code_for(exc.error_code),
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "detail": exc.context,
        },
    )


async def _publication_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Wrap PATCH admin/publications validation errors with structured code."""
    if request.url.path.startswith("/api/v1/admin/publications/") and request.method == "PATCH":
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=jsonable_encoder(
                {
                    "detail": {
                        "error_code": "PUBLICATION_UPDATE_PAYLOAD_INVALID",
                        "message": "The submitted changes are invalid.",
                        "details": {"validation_errors": exc.errors()},
                    }
                }
            ),
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


async def _publication_precondition_failed_exception_handler(
    request: Request,
    exc: PublicationPreconditionFailedError,
) -> JSONResponse:
    """Emit 412 envelope with mandatory jsonable_encoder wrapping.

    jsonable_encoder is REQUIRED — see TEST_INFRASTRUCTURE.md §2.1 / DEBT-030
    PR1 lesson. Without it, Pydantic v2 internals can produce non-JSON-
    serializable objects in ``details``, causing JSONResponse to fail and
    the handler to surface 500 instead of 412.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"detail": exc.detail}),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the given FastAPI application.

    Call this once during application startup::

        register_exception_handlers(app)
    """
    app.add_exception_handler(
        SummaVisionError,
        _summa_vision_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(RequestValidationError, _publication_validation_exception_handler)
    app.add_exception_handler(
        PublicationPreconditionFailedError,
        _publication_precondition_failed_exception_handler,  # type: ignore[arg-type]
    )
