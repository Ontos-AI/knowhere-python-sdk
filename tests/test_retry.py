"""Tests for the retry logic: retryable statuses, backoff, max retries."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
import pytest
import respx

from knowhere._exceptions import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
)
from tests.conftest import BASE_URL


JOBS_URL: str = f"{BASE_URL}/v1/jobs"
JOB_ID: str = "job_retry_test"
GET_URL: str = f"{JOBS_URL}/{JOB_ID}"

DONE_RESPONSE: Dict[str, Any] = {
    "job_id": JOB_ID,
    "status": "done",
    "source_type": "url",
    "result_url": "https://storage.example.com/result.zip",
}


def _error_body(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build an error response body."""
    error: Dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": "req_retry",
    }
    if details is not None:
        error["details"] = details
    return {"success": False, "error": error}


# ---------------------------------------------------------------------------
# 503 triggers retry
# ---------------------------------------------------------------------------


class TestRetry503:
    """Verify 503 responses trigger automatic retry."""

    @respx.mock
    def test_503_triggers_retry(self, sync_client: Any) -> None:
        route = respx.get(GET_URL).mock(
            side_effect=[
                httpx.Response(
                    503,
                    json=_error_body("UNAVAILABLE", "Service unavailable"),
                    headers={"retry-after": "0"},
                ),
                httpx.Response(200, json=DONE_RESPONSE),
            ]
        )

        result = sync_client.jobs.get(JOB_ID)

        assert result.status == "done"
        assert route.call_count == 2


# ---------------------------------------------------------------------------
# 504 triggers retry
# ---------------------------------------------------------------------------


class TestRetry504:
    """Verify 504 responses trigger automatic retry."""

    @respx.mock
    def test_504_triggers_retry(self, sync_client: Any) -> None:
        route = respx.get(GET_URL).mock(
            side_effect=[
                httpx.Response(
                    504,
                    json=_error_body("DEADLINE_EXCEEDED", "Gateway timeout"),
                    headers={"retry-after": "0"},
                ),
                httpx.Response(200, json=DONE_RESPONSE),
            ]
        )

        result = sync_client.jobs.get(JOB_ID)

        assert result.status == "done"
        assert route.call_count == 2


# ---------------------------------------------------------------------------
# 429 with retry_after in body details triggers retry
# ---------------------------------------------------------------------------


class TestRetry429WithRetryAfter:
    """Verify 429 with details.retry_after triggers retry."""

    @respx.mock
    def test_429_with_retry_after_in_body_retries(
        self, sync_client: Any
    ) -> None:
        route = respx.get(GET_URL).mock(
            side_effect=[
                httpx.Response(
                    429,
                    json=_error_body(
                        "RESOURCE_EXHAUSTED",
                        "Rate limited",
                        details={"retry_after": 0},
                    ),
                ),
                httpx.Response(200, json=DONE_RESPONSE),
            ]
        )

        result = sync_client.jobs.get(JOB_ID)

        assert result.status == "done"
        assert route.call_count == 2


# ---------------------------------------------------------------------------
# 429 without retry_after does NOT retry (quota exceeded)
# ---------------------------------------------------------------------------


class TestNoRetry429WithoutRetryAfter:
    """Verify 429 without retry_after does NOT retry (quota exceeded)."""

    @respx.mock
    def test_429_without_retry_after_does_not_retry(
        self, sync_client: Any
    ) -> None:
        route = respx.get(GET_URL).mock(
            return_value=httpx.Response(
                429,
                json=_error_body(
                    "RESOURCE_EXHAUSTED", "Quota exceeded"
                ),
            )
        )

        with pytest.raises(RateLimitError):
            sync_client.jobs.get(JOB_ID)

        assert route.call_count == 1


# ---------------------------------------------------------------------------
# 400 does NOT retry
# ---------------------------------------------------------------------------


class TestNoRetry400:
    """Verify 400 responses are NOT retried."""

    @respx.mock
    def test_400_does_not_retry(self, sync_client: Any) -> None:
        route = respx.get(GET_URL).mock(
            return_value=httpx.Response(
                400,
                json=_error_body("INVALID_ARGUMENT", "Bad request"),
            )
        )

        with pytest.raises(BadRequestError):
            sync_client.jobs.get(JOB_ID)

        assert route.call_count == 1


# ---------------------------------------------------------------------------
# 401 does NOT retry
# ---------------------------------------------------------------------------


class TestNoRetry401:
    """Verify 401 responses are NOT retried."""

    @respx.mock
    def test_401_does_not_retry(self, sync_client: Any) -> None:
        route = respx.get(GET_URL).mock(
            return_value=httpx.Response(
                401,
                json=_error_body("UNAUTHENTICATED", "Invalid API key"),
            )
        )

        with pytest.raises(AuthenticationError):
            sync_client.jobs.get(JOB_ID)

        assert route.call_count == 1


# ---------------------------------------------------------------------------
# Max retries exceeded
# ---------------------------------------------------------------------------


class TestMaxRetriesExceeded:
    """Verify that exceeding max retries raises the last error."""

    @respx.mock
    def test_max_retries_raises_last_error(self, sync_client: Any) -> None:
        """After exhausting all retries, the last error should be raised."""
        # Create enough 503 responses to exceed max_retries (default 5)
        responses = [
            httpx.Response(
                503,
                json=_error_body("UNAVAILABLE", "Service unavailable"),
                headers={"retry-after": "0"},
            )
            for _ in range(10)
        ]
        route = respx.get(GET_URL).mock(side_effect=responses)

        with pytest.raises(ServiceUnavailableError):
            sync_client.jobs.get(JOB_ID)

        # Should have been called max_retries + 1 times (initial + retries)
        assert route.call_count >= 2


# ---------------------------------------------------------------------------
# Connection error triggers retry
# ---------------------------------------------------------------------------


class TestRetryConnectionError:
    """Verify connection errors trigger automatic retry."""

    @respx.mock
    def test_connection_error_triggers_retry(
        self, sync_client: Any
    ) -> None:
        route = respx.get(GET_URL).mock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                httpx.Response(200, json=DONE_RESPONSE),
            ]
        )

        result = sync_client.jobs.get(JOB_ID)

        assert result.status == "done"
        assert route.call_count == 2


# ---------------------------------------------------------------------------
# 409 (ABORTED) triggers retry
# ---------------------------------------------------------------------------


class TestRetry409:
    """Verify 409 ABORTED responses trigger automatic retry."""

    @respx.mock
    def test_409_triggers_retry(self, sync_client: Any) -> None:
        route = respx.get(GET_URL).mock(
            side_effect=[
                httpx.Response(
                    409,
                    json=_error_body("ABORTED", "Concurrency conflict"),
                ),
                httpx.Response(200, json=DONE_RESPONSE),
            ]
        )

        result = sync_client.jobs.get(JOB_ID)

        assert result.status == "done"
        assert route.call_count == 2


# ---------------------------------------------------------------------------
# 500 does NOT retry
# ---------------------------------------------------------------------------


class TestNoRetry500:
    """Verify 500 INTERNAL_ERROR responses are NOT retried."""

    @respx.mock
    def test_500_does_not_retry(self, sync_client: Any) -> None:
        route = respx.get(GET_URL).mock(
            return_value=httpx.Response(
                500,
                json=_error_body("INTERNAL_ERROR", "Internal server error"),
            )
        )

        with pytest.raises(InternalServerError):
            sync_client.jobs.get(JOB_ID)

        assert route.call_count == 1


# ---------------------------------------------------------------------------
# 502 triggers retry (maps to UNAVAILABLE)
# ---------------------------------------------------------------------------


class TestRetry502:
    """Verify 502 responses trigger automatic retry."""

    @respx.mock
    def test_502_triggers_retry(self, sync_client: Any) -> None:
        route = respx.get(GET_URL).mock(
            side_effect=[
                httpx.Response(
                    502,
                    json=_error_body("UNAVAILABLE", "Bad gateway"),
                ),
                httpx.Response(200, json=DONE_RESPONSE),
            ]
        )

        result = sync_client.jobs.get(JOB_ID)

        assert result.status == "done"
        assert route.call_count == 2
