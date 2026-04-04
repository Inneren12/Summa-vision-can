"""Tests for the structured logging configuration.

Coverage targets:
- ``setup_logging()`` produces valid JSON when ``ENVIRONMENT=prod``.
- ``setup_logging()`` uses ``ConsoleRenderer`` when ``ENVIRONMENT=local``.
- ``get_logger()`` returns a usable bound logger.
- ``force_json`` parameter overrides the environment check.
- Repeated ``setup_logging()`` calls do not stack handlers.
"""

from __future__ import annotations

import json
import logging
import os
from io import StringIO
from typing import TYPE_CHECKING
from unittest.mock import patch

from src.core.logging import get_logger, setup_logging

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_log_output(logger_name: str, message: str) -> str:
    """Emit a log line and capture what the root handler writes."""
    buf = StringIO()
    root = logging.getLogger()

    # Temporarily replace the handler stream to capture output.
    original_handlers = root.handlers[:]
    for h in root.handlers:
        if isinstance(h, logging.StreamHandler):
            h.stream = buf

    stdlib_logger = logging.getLogger(logger_name)
    stdlib_logger.info(message)

    output = buf.getvalue()

    # Restore original streams.
    for h, orig_h in zip(root.handlers, original_handlers):
        if isinstance(h, logging.StreamHandler) and isinstance(
            orig_h, logging.StreamHandler
        ):
            h.stream = orig_h.stream

    return output


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSetupLoggingJSON:
    """Verify JSON rendering in production mode."""

    def test_json_output_when_env_is_prod(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "prod"}):
            setup_logging()

        output = _capture_log_output("test.json_prod", "hello from prod")
        # The output should be valid JSON.
        parsed = json.loads(output)
        assert parsed["event"] == "hello from prod"
        assert "timestamp" in parsed
        assert parsed["level"] == "info"

    def test_force_json_overrides_local_env(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
            setup_logging(force_json=True)

        output = _capture_log_output("test.force_json", "forced json")
        parsed = json.loads(output)
        assert parsed["event"] == "forced json"


class TestSetupLoggingConsole:
    """Verify console rendering in local/development mode."""

    def test_console_output_when_env_is_local(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
            setup_logging()

        output = _capture_log_output("test.console", "hello console")
        # ConsoleRenderer does NOT produce JSON; it produces human-readable
        # coloured output.  We just verify the event text appears.
        assert "hello console" in output

    def test_console_output_when_env_is_unset(self) -> None:
        """Default (no ENVIRONMENT var) should use console renderer."""
        env = os.environ.copy()
        env.pop("ENVIRONMENT", None)
        with patch.dict(os.environ, env, clear=True):
            setup_logging()

        output = _capture_log_output("test.default", "default console")
        assert "default console" in output


class TestGetLogger:
    """Verify that ``get_logger`` returns a usable bound logger."""

    def test_returns_bound_logger(self) -> None:
        setup_logging(force_json=True)
        log = get_logger(service="unit_test")
        # structlog bound loggers expose standard level methods.
        assert callable(log.info)
        assert callable(log.error)
        assert callable(log.warning)
        assert callable(log.debug)

    def test_initial_bindings_included_in_output(self) -> None:
        setup_logging(force_json=True)
        log = get_logger(service="binding_test")

        buf = StringIO()
        root = logging.getLogger()
        for h in root.handlers:
            if isinstance(h, logging.StreamHandler):
                h.stream = buf

        log.info("binding check")
        output = buf.getvalue()
        parsed = json.loads(output)
        assert parsed["service"] == "binding_test"
        assert parsed["event"] == "binding check"


class TestHandlerIdempotency:
    """Repeated ``setup_logging`` calls must NOT duplicate handlers."""

    def test_no_duplicate_handlers(self) -> None:
        setup_logging(force_json=True)
        setup_logging(force_json=True)
        setup_logging(force_json=True)

        root = logging.getLogger()
        assert len(root.handlers) == 1
