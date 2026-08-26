"""Structured logging conventions used throughout the pipeline."""

from __future__ import annotations

import logging
from typing import Any, Literal

import structlog

__all__ = ["configure_logging", "get_logger"]

RenderingStyle = Literal["console", "json"]


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Returns the logger a module should bind its records to."""
    return structlog.stdlib.get_logger(name)


def configure_logging(
    *,
    level: int = logging.INFO,
    rendering: RenderingStyle = "console",
) -> None:
    """Configures structlog and the standard library logging bridge."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]
    renderer: Any = (
        structlog.dev.ConsoleRenderer()
        if rendering == "console"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", level=level)
