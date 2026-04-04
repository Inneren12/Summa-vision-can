"""Tests for the exception hierarchy and the global error handler.

Coverage targets:
- Every exception subclass can be instantiated with defaults and custom args.
- The global handler returns the standard JSON envelope.
- The handler logs the error via *structlog* with context, traceback,
  and service_name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.error_handler import register_exception_handlers
from src.core.exceptions import (
    AIServiceError,
    AuthError,
    DataSourceError,
    StorageError,
    SummaVisionError,
    ValidationError,
)
from src.core.logging import setup_logging

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

setup_logging(force_json=True)


def _make_app() -> FastAPI:
    """Return a minimal FastAPI app with the global handler registered."""
    app = FastAPI()
    register_exception_handlers(app)
    return app


# ---------------------------------------------------------------------------
# Exception hierarchy unit tests
# ---------------------------------------------------------------------------


class TestSummaVisionError:
    """Verify the base exception carries the expected attributes."""

    def test_defaults(self) -> None:
        exc = SummaVisionError()
        assert exc.message == "An unexpected error occurred"
        assert exc.error_code == "SUMMA_VISION_ERROR"
        assert exc.context == {}
        assert str(exc) == "An unexpected error occurred"

    def test_custom_values(self) -> None:
        ctx = {"key": "value"}
        exc = SummaVisionError(
            message="boom", error_code="CUSTOM", context=ctx
        )
        assert exc.message == "boom"
        assert exc.error_code == "CUSTOM"
        assert exc.context == ctx

    def test_is_exception(self) -> None:
        assert issubclass(SummaVisionError, Exception)


class TestDataSourceError:
    """Verify DataSourceError defaults and inheritance."""

    def test_defaults(self) -> None:
        exc = DataSourceError()
        assert exc.message == "Data source error"
        assert exc.error_code == "DATASOURCE_ERROR"
        assert isinstance(exc, SummaVisionError)

    def test_custom_values(self) -> None:
        exc = DataSourceError(
            message="StatCan down",
            error_code="STATCAN_503",
            context={"status": 503},
        )
        assert exc.message == "StatCan down"
        assert exc.error_code == "STATCAN_503"
        assert exc.context == {"status": 503}


class TestAIServiceError:
    """Verify AIServiceError defaults and inheritance."""

    def test_defaults(self) -> None:
        exc = AIServiceError()
        assert exc.message == "AI service error"
        assert exc.error_code == "AI_SERVICE_ERROR"
        assert isinstance(exc, SummaVisionError)

    def test_custom_values(self) -> None:
        exc = AIServiceError(
            message="Gemini quota exhausted",
            error_code="LLM_QUOTA",
            context={"provider": "gemini"},
        )
        assert exc.message == "Gemini quota exhausted"
        assert exc.context == {"provider": "gemini"}


class TestStorageError:
    """Verify StorageError defaults and inheritance."""

    def test_defaults(self) -> None:
        exc = StorageError()
        assert exc.message == "Storage error"
        assert exc.error_code == "STORAGE_ERROR"
        assert isinstance(exc, SummaVisionError)

    def test_custom_values(self) -> None:
        exc = StorageError(
            message="S3 upload failed", context={"bucket": "my-bucket"}
        )
        assert exc.message == "S3 upload failed"
        assert exc.context == {"bucket": "my-bucket"}


class TestValidationError:
    """Verify ValidationError defaults and inheritance."""

    def test_defaults(self) -> None:
        exc = ValidationError()
        assert exc.message == "Validation error"
        assert exc.error_code == "VALIDATION_ERROR"
        assert isinstance(exc, SummaVisionError)

    def test_custom_values(self) -> None:
        exc = ValidationError(
            message="Score out of range",
            context={"score": 11, "max": 10},
        )
        assert exc.message == "Score out of range"
        assert exc.context == {"score": 11, "max": 10}


class TestAuthError:
    """Verify AuthError defaults and inheritance."""

    def test_defaults(self) -> None:
        exc = AuthError()
        assert exc.message == "Authentication error"
        assert exc.error_code == "AUTH_ERROR"
        assert isinstance(exc, SummaVisionError)

    def test_custom_values(self) -> None:
        exc = AuthError(
            message="Token expired",
            error_code="TOKEN_EXPIRED",
            context={"token_type": "jwt"},
        )
        assert exc.message == "Token expired"
        assert exc.error_code == "TOKEN_EXPIRED"
        assert exc.context == {"token_type": "jwt"}


# ---------------------------------------------------------------------------
# Error handler integration tests (via TestClient)
# ---------------------------------------------------------------------------


class TestGlobalErrorHandler:
    """Verify the global handler produces the expected JSON envelope."""

    def test_summa_vision_error_returns_standard_json(self) -> None:
        app = _make_app()

        @app.get("/raise-base")
        async def _raise_base() -> None:
            raise SummaVisionError(
                message="something broke",
                error_code="BASE_ERR",
                context={"detail_key": "detail_value"},
            )

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/raise-base")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error_code"] == "BASE_ERR"
        assert body["message"] == "something broke"
        assert body["detail"] == {"detail_key": "detail_value"}

    def test_datasource_error_returns_502(self) -> None:
        app = _make_app()

        @app.get("/raise-ds")
        async def _raise_ds() -> None:
            raise DataSourceError(message="API unavailable")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/raise-ds")
        assert resp.status_code == 502
        body = resp.json()
        assert body["error_code"] == "DATASOURCE_ERROR"
        assert body["message"] == "API unavailable"

    def test_ai_service_error_returns_502(self) -> None:
        app = _make_app()

        @app.get("/raise-ai")
        async def _raise_ai() -> None:
            raise AIServiceError(message="LLM timeout")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/raise-ai")
        assert resp.status_code == 502
        body = resp.json()
        assert body["error_code"] == "AI_SERVICE_ERROR"

    def test_storage_error_returns_500(self) -> None:
        app = _make_app()

        @app.get("/raise-storage")
        async def _raise_storage() -> None:
            raise StorageError()

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/raise-storage")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error_code"] == "STORAGE_ERROR"

    def test_validation_error_returns_422(self) -> None:
        app = _make_app()

        @app.get("/raise-val")
        async def _raise_val() -> None:
            raise ValidationError(message="bad input")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/raise-val")
        assert resp.status_code == 422
        body = resp.json()
        assert body["error_code"] == "VALIDATION_ERROR"

    def test_auth_error_returns_401(self) -> None:
        app = _make_app()

        @app.get("/raise-auth")
        async def _raise_auth() -> None:
            raise AuthError()

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/raise-auth")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error_code"] == "AUTH_ERROR"

    def test_handler_logs_exception_via_structlog(self) -> None:
        """Assert that structlog.error is called with context and traceback."""
        app = _make_app()

        @app.get("/raise-logged")
        async def _raise_logged() -> None:
            raise DataSourceError(
                message="log me",
                error_code="LOG_TEST",
                context={"foo": "bar"},
            )

        with patch("src.core.error_handler.logger") as mock_logger:
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/raise-logged")
            assert resp.status_code == 500  # LOG_TEST isn't in the mapping

            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args
            # Positional arg is the message
            assert call_kwargs[0][0] == "log me"
            # Keyword args must include context, traceback, and service_name
            assert call_kwargs[1]["error_code"] == "LOG_TEST"
            assert call_kwargs[1]["context"] == {"foo": "bar"}
            assert call_kwargs[1]["service_name"] == "summa_vision"
            assert "traceback" in call_kwargs[1]
            assert isinstance(call_kwargs[1]["traceback"], list)

    def test_empty_context_returns_empty_detail(self) -> None:
        app = _make_app()

        @app.get("/raise-empty")
        async def _raise_empty() -> None:
            raise SummaVisionError(message="no ctx", error_code="NO_CTX")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/raise-empty")
        body = resp.json()
        assert body["detail"] == {}

    def test_subclass_caught_by_base_handler(self) -> None:
        """Verify that the base SummaVisionError handler catches subclasses."""
        app = _make_app()

        @app.get("/raise-sub")
        async def _raise_sub() -> None:
            raise AuthError(
                message="sub caught",
                error_code="AUTH_ERROR",
                context={"sub": True},
            )

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/raise-sub")
        assert resp.status_code == 401
        body = resp.json()
        assert body["message"] == "sub caught"
        assert body["detail"] == {"sub": True}
