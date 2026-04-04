"""Global FastAPI exception handler for :class:`SummaVisionError`.

This module registers a single handler that intercepts every exception in the
``SummaVisionError`` hierarchy, logs the error together with its structured
context via *structlog*, and returns a deterministic JSON envelope to the
client.

Usage::

    from fastapi import FastAPI
    from src.core.error_handler import register_exception_handlers

    app = FastAPI()
    register_exception_handlers(app)
"""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

from src.core.exceptions import SummaVisionError
from src.core.logging import get_logger

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


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the given FastAPI application.

    Call this once during application startup::

        register_exception_handlers(app)
    """
    app.add_exception_handler(
        SummaVisionError,
        _summa_vision_exception_handler,  # type: ignore[arg-type]
    )
