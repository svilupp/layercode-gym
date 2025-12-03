from __future__ import annotations

"""Centralised logging configuration for Layercode Gym."""

import logging
import logfire
import os
import re
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


# Patterns for sensitive data that should be redacted from error messages
_SENSITIVE_PATTERNS: Final[list[tuple[re.Pattern[str], str]]] = [
    # OpenAI API keys: sk-... or sk-proj-...
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED_OPENAI_KEY]"),
    # Logfire tokens: pylf_...
    (re.compile(r"\bpylf_[A-Za-z0-9_-]+\b"), "[REDACTED_LOGFIRE_TOKEN]"),
    # Bearer tokens in headers
    (re.compile(r"Bearer\s+[A-Za-z0-9_.-]+", re.IGNORECASE), "Bearer [REDACTED]"),
    # Authorization header values
    (
        re.compile(r"['\"]?Authorization['\"]?\s*:\s*['\"]?[^'\"}\s]+", re.IGNORECASE),
        "'Authorization': '[REDACTED]'",
    ),
    # Generic API key patterns in headers/URLs
    (
        re.compile(
            r"['\"]?api[_-]?key['\"]?\s*[=:]\s*['\"]?[A-Za-z0-9_.-]+", re.IGNORECASE
        ),
        "api_key=[REDACTED]",
    ),
    # X-API-Key header
    (
        re.compile(r"['\"]?X-API-Key['\"]?\s*:\s*['\"]?[^'\"}\s]+", re.IGNORECASE),
        "'X-API-Key': '[REDACTED]'",
    ),
    # password/secret fields
    (
        re.compile(
            r"['\"]?(?:password|secret)['\"]?\s*[=:]\s*['\"]?[^'\"}\s]+", re.IGNORECASE
        ),
        "password=[REDACTED]",
    ),
]


def sanitize_error(error: BaseException | str) -> str:
    """Sanitize an error message by redacting sensitive information.

    Removes API keys, tokens, passwords, and other sensitive data from
    error messages to prevent accidental exposure in logs or CI output.

    Args:
        error: An exception or error message string to sanitize.

    Returns:
        A sanitized string with sensitive patterns replaced.
    """
    text = str(error)

    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)

    return text
