"""Logging utilities for the Knowhere SDK."""

from __future__ import annotations

import logging
import os
import re
from typing import Mapping

from knowhere._constants import ENV_LOG_LEVEL

_logger: logging.Logger = logging.getLogger("knowhere")

_LEVEL_NAME: str = os.environ.get(ENV_LOG_LEVEL, "WARNING").upper()
_logger.setLevel(getattr(logging, _LEVEL_NAME, logging.WARNING))

if not _logger.handlers:
    _handler: logging.StreamHandler = logging.StreamHandler()  # type: ignore[type-arg]
    _handler.setFormatter(
        logging.Formatter("[%(levelname)s] knowhere: %(message)s")
    )
    _logger.addHandler(_handler)

_AUTH_PATTERN: re.Pattern[str] = re.compile(
    r"(Bearer\s+)(\S+)", flags=re.IGNORECASE
)


def getLogger() -> logging.Logger:
    """Return the SDK-wide logger."""
    return _logger


def redactSensitiveHeaders(
    headers: Mapping[str, str],
) -> dict[str, str]:
    """Return a copy of *headers* with Authorization values redacted.

    The redacted form is ``Bearer sk_...REDACTED`` so that log output never
    leaks API keys while still showing that a key was present.
    """
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            redacted[key] = _AUTH_PATTERN.sub(r"\1sk_...REDACTED", value)
        else:
            redacted[key] = value
    return redacted
