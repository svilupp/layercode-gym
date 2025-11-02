from __future__ import annotations

"""Centralised logging configuration for Layercode Gym."""

import logging
import logfire
import os
from typing import Final

_LOGGER_NAME: Final = "layercode_gym"


def configure_logging() -> logging.Logger:
    """Configure and return the package root logger.

    The configuration is idempotent – calling multiple times returns the same logger
    without recreating handlers.
    """

    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    logger.propagate = False

    # Configure Logfire if LOGFIRE_TOKEN is present

    logfire.configure(
        scrubbing=False,
        service_name="client",
        send_to_logfire="if-token-present",
        environment=os.getenv("APP_ENV", "development"),
    )
    logfire.instrument_pydantic_ai()
    logfire.instrument_openai()

    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{_LOGGER_NAME}.{name}")
