"""Structured logging configuration powered by *structlog*.

The renderer is selected dynamically based on the ``ENVIRONMENT`` env-var:

* ``"prod"`` (or any non-local value) → :class:`structlog.dev.ConsoleRenderer`
  is **not** used; instead we emit **JSON lines** via
  :class:`structlog.processors.JSONRenderer`.
* ``"local"`` (default) → pretty-printed, coloured console output via
  :class:`structlog.dev.ConsoleRenderer`.

Call :func:`setup_logging` once at application startup (typically in
``main.py`` or an ASGI lifespan handler) to wire everything up.

Usage::

    from src.core.logging import setup_logging, get_logger

    setup_logging()                      # call once
    logger = get_logger()                # per-module logger
    logger.info("startup", version="0.1")
"""

from __future__ import annotations

import logging
import os
import sys

import structlog


def _is_local_environment() -> bool:
    """Return ``True`` when running in local/development mode.

    The check reads ``ENVIRONMENT`` from the process environment and falls
    back to ``"local"`` when the variable is absent.
    """
    return os.getenv("ENVIRONMENT", "local").lower() == "local"


def setup_logging(*, force_json: bool = False) -> None:
    """Configure *structlog* and the stdlib root logger.

    Args:
        force_json: When ``True``, always use JSON rendering regardless of
            the ``ENVIRONMENT`` variable.  Useful for testing.
    """
    use_json = force_json or not _is_local_environment()

    # Processors shared between structlog-native and stdlib loggers.
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if use_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # foreign_pre_chain handles events originating from stdlib loggers
        # (e.g. ``logging.getLogger("x").info(...)``).
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # Prevent duplicate handlers on repeated calls (e.g. tests).
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def get_logger(**initial_bindings: object) -> structlog.stdlib.BoundLogger:
    """Return a *structlog* bound logger.

    Any keyword arguments are bound as initial context:

        logger = get_logger(service="etl")
        logger.info("started")  # includes service="etl" automatically
    """
    return structlog.get_logger(**initial_bindings)
