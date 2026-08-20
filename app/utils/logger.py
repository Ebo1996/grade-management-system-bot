"""
Structured logging configuration.

Uses structlog for consistent, structured log output.
In development: pretty colored console output.
In production: JSON output suitable for log aggregation.

IMPORTANT: Never log bot tokens, passwords, or raw result data.
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger


def _drop_color_message_key(
    _logger: WrappedLogger, _method_name: str, event_dict: EventDict
) -> EventDict:
    """Remove the internal uvicorn color_message key if present."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """
    Configure structlog and stdlib logging.

    Args:
        log_level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
        environment: 'development' for pretty output, anything else for JSON.
    """
    log_level_int = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _drop_color_message_key,
    ]

    if environment == "development":
        # Human-friendly output for local development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Machine-readable JSON for staging / production
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.make_filtering_bound_logger(log_level_int),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so that aiogram and SQLAlchemy
    # messages are captured through structlog.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level_int,
    )
    for noisy_logger in ("aiogram", "sqlalchemy.engine"):
        logging.getLogger(noisy_logger).setLevel(
            logging.WARNING if environment == "production" else log_level_int
        )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Return a named structlog logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("user_action", telegram_id=12345, action="view_results")
    """
    return structlog.get_logger(name)  # type: ignore[return-value]
