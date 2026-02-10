"""Tests for the logging module: header redaction and logger configuration."""

from __future__ import annotations

import logging
from typing import Dict

from knowhere._logging import getLogger, redactSensitiveHeaders


# ---------------------------------------------------------------------------
# redactSensitiveHeaders
# ---------------------------------------------------------------------------


class TestRedactSensitiveHeaders:
    """Verify that sensitive header values are properly redacted."""

    def test_redacts_authorization_bearer(self) -> None:
        headers: Dict[str, str] = {
            "Authorization": "Bearer sk_live_abc123xyz",
            "Content-Type": "application/json",
        }
        redacted: Dict[str, str] = redactSensitiveHeaders(headers)
        assert redacted["Authorization"] == "Bearer sk_...REDACTED"

    def test_preserves_non_sensitive_headers(self) -> None:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Request-Id": "req_abc",
        }
        redacted: Dict[str, str] = redactSensitiveHeaders(headers)
        assert redacted["Content-Type"] == "application/json"
        assert redacted["Accept"] == "application/json"
        assert redacted["X-Request-Id"] == "req_abc"

    def test_case_insensitive_authorization(self) -> None:
        headers: Dict[str, str] = {
            "authorization": "Bearer sk_test_key",
        }
        redacted: Dict[str, str] = redactSensitiveHeaders(headers)
        assert "REDACTED" in redacted["authorization"]
        assert "sk_test_key" not in redacted["authorization"]

    def test_returns_new_dict(self) -> None:
        headers: Dict[str, str] = {"Authorization": "Bearer key"}
        redacted: Dict[str, str] = redactSensitiveHeaders(headers)
        assert redacted is not headers

    def test_empty_headers(self) -> None:
        headers: Dict[str, str] = {}
        redacted: Dict[str, str] = redactSensitiveHeaders(headers)
        assert redacted == {}

    def test_non_bearer_authorization(self) -> None:
        """Non-Bearer authorization values should still be handled."""
        headers: Dict[str, str] = {
            "Authorization": "Basic dXNlcjpwYXNz",
        }
        redacted: Dict[str, str] = redactSensitiveHeaders(headers)
        # The regex only matches Bearer tokens, so Basic should pass through
        assert redacted["Authorization"] == "Basic dXNlcjpwYXNz"


# ---------------------------------------------------------------------------
# Logger configuration
# ---------------------------------------------------------------------------


class TestLoggerConfiguration:
    """Verify the SDK logger is properly configured."""

    def test_logger_name_is_knowhere(self) -> None:
        logger: logging.Logger = getLogger()
        assert logger.name == "knowhere"

    def test_logger_is_singleton(self) -> None:
        logger_a: logging.Logger = getLogger()
        logger_b: logging.Logger = getLogger()
        assert logger_a is logger_b

    def test_logger_has_handler(self) -> None:
        logger: logging.Logger = getLogger()
        assert len(logger.handlers) > 0
