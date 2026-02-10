"""Tests for the exception hierarchy and factory functions."""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

import httpx
import pytest

from knowhere._exceptions import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ChecksumError,
    ConflictError,
    GatewayTimeoutError,
    InternalServerError,
    JobFailedError,
    KnowhereError,
    NotFoundError,
    PaymentRequiredError,
    PermissionDeniedError,
    PollingTimeoutError,
    RateLimitError,
    ServiceUnavailableError,
    _STATUS_TO_EXCEPTION,
    makeStatusError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: int,
    headers: Optional[Dict[str, str]] = None,
) -> httpx.Response:
    """Build a minimal httpx.Response for testing."""
    return httpx.Response(
        status_code=status_code,
        headers=headers or {},
        request=httpx.Request("GET", "https://api.test.knowhereto.ai/v1/jobs/j1"),
    )


# ---------------------------------------------------------------------------
# _STATUS_TO_EXCEPTION mapping
# ---------------------------------------------------------------------------


class TestStatusToExceptionMapping:
    """Verify that _STATUS_TO_EXCEPTION maps all expected status codes."""

    EXPECTED_MAPPING: Dict[int, Type[APIStatusError]] = {
        400: BadRequestError,
        401: AuthenticationError,
        402: PaymentRequiredError,
        403: PermissionDeniedError,
        404: NotFoundError,
        409: ConflictError,
        429: RateLimitError,
        500: InternalServerError,
        502: ServiceUnavailableError,
        503: ServiceUnavailableError,
        504: GatewayTimeoutError,
    }

    def test_all_expected_codes_present(self) -> None:
        assert set(_STATUS_TO_EXCEPTION.keys()) == set(self.EXPECTED_MAPPING.keys())

    @pytest.mark.parametrize(
        "status_code,expected_class",
        [
            (400, BadRequestError),
            (401, AuthenticationError),
            (402, PaymentRequiredError),
            (403, PermissionDeniedError),
            (404, NotFoundError),
            (409, ConflictError),
            (429, RateLimitError),
            (500, InternalServerError),
            (502, ServiceUnavailableError),
            (503, ServiceUnavailableError),
            (504, GatewayTimeoutError),
        ],
    )
    def test_mapping_value(
        self, status_code: int, expected_class: Type[APIStatusError]
    ) -> None:
        assert _STATUS_TO_EXCEPTION[status_code] is expected_class


# ---------------------------------------------------------------------------
# makeStatusError factory
# ---------------------------------------------------------------------------


class TestMakeStatusError:
    """Verify makeStatusError creates the correct exception type."""

    def test_creates_bad_request_error(self) -> None:
        response: httpx.Response = _make_response(400)
        body: Dict[str, Any] = {
            "error": {"code": "INVALID_ARGUMENT", "message": "Bad input"}
        }
        exc: APIStatusError = makeStatusError(400, response, body)
        assert isinstance(exc, BadRequestError)
        assert exc.status_code == 400
        assert exc.code == "INVALID_ARGUMENT"

    def test_creates_authentication_error(self) -> None:
        response: httpx.Response = _make_response(401)
        body: Dict[str, Any] = {
            "error": {"code": "UNAUTHENTICATED", "message": "Invalid key"}
        }
        exc: APIStatusError = makeStatusError(401, response, body)
        assert isinstance(exc, AuthenticationError)

    def test_creates_not_found_error(self) -> None:
        response: httpx.Response = _make_response(404)
        body: Dict[str, Any] = {
            "error": {
                "code": "NOT_FOUND",
                "message": "Job not found",
                "request_id": "req_abc123",
            }
        }
        exc: APIStatusError = makeStatusError(404, response, body)
        assert isinstance(exc, NotFoundError)
        assert exc.request_id == "req_abc123"

    def test_creates_rate_limit_error_with_retry_after(self) -> None:
        response: httpx.Response = _make_response(429, {"retry-after": "5"})
        body: Dict[str, Any] = {
            "error": {"code": "RESOURCE_EXHAUSTED", "message": "Too many requests"}
        }
        exc: APIStatusError = makeStatusError(429, response, body)
        assert isinstance(exc, RateLimitError)
        assert isinstance(exc, RateLimitError) and exc.retry_after == 5.0

    def test_creates_service_unavailable_error(self) -> None:
        response: httpx.Response = _make_response(503, {"retry-after": "10"})
        exc: APIStatusError = makeStatusError(503, response)
        assert isinstance(exc, ServiceUnavailableError)
        assert exc.retry_after == 10.0

    def test_creates_gateway_timeout_error(self) -> None:
        response: httpx.Response = _make_response(504, {"retry-after": "30"})
        exc: APIStatusError = makeStatusError(504, response)
        assert isinstance(exc, GatewayTimeoutError)
        assert exc.retry_after == 30.0

    def test_unknown_status_falls_back_to_api_status_error(self) -> None:
        response: httpx.Response = _make_response(418)
        exc: APIStatusError = makeStatusError(418, response)
        assert type(exc) is APIStatusError
        assert exc.status_code == 418

    def test_extracts_fields_from_body(self) -> None:
        response: httpx.Response = _make_response(400)
        body: Dict[str, Any] = {
            "error": {
                "code": "INVALID_ARGUMENT",
                "message": "Missing field",
                "request_id": "req_xyz",
                "details": {"field": "url"},
            }
        }
        exc: APIStatusError = makeStatusError(400, response, body)
        assert exc.code == "INVALID_ARGUMENT"
        assert exc.request_id == "req_xyz"
        assert exc.details == {"field": "url"}
        assert exc.body == body

    def test_no_body_uses_defaults(self) -> None:
        response: httpx.Response = _make_response(500)
        exc: APIStatusError = makeStatusError(500, response)
        assert exc.code == "unknown"
        assert exc.request_id is None
        assert exc.details is None


# ---------------------------------------------------------------------------
# APIStatusError attributes
# ---------------------------------------------------------------------------


class TestAPIStatusErrorAttributes:
    """Verify APIStatusError carries all expected attributes."""

    def test_carries_status_code(self) -> None:
        response: httpx.Response = _make_response(404)
        exc: APIStatusError = APIStatusError(
            404, code="NOT_FOUND", message="Not found", response=response
        )
        assert exc.status_code == 404

    def test_carries_code_and_message(self) -> None:
        response: httpx.Response = _make_response(400)
        exc: APIStatusError = APIStatusError(
            400, code="BAD", message="Bad request", response=response
        )
        assert exc.code == "BAD"
        assert "BAD" in str(exc)
        assert "Bad request" in str(exc)

    def test_carries_request_id(self) -> None:
        response: httpx.Response = _make_response(500)
        exc: APIStatusError = APIStatusError(
            500, code="ERR", message="err", request_id="req_1", response=response
        )
        assert exc.request_id == "req_1"
        assert "req_1" in str(exc)

    def test_carries_details_and_body(self) -> None:
        response: httpx.Response = _make_response(400)
        body: Dict[str, str] = {"error": "test"}
        exc: APIStatusError = APIStatusError(
            400,
            code="ERR",
            message="err",
            details={"x": 1},
            body=body,
            response=response,
        )
        assert exc.details == {"x": 1}
        assert exc.body == body


# ---------------------------------------------------------------------------
# Retryable error retry_after
# ---------------------------------------------------------------------------


class TestRetryAfterAttribute:
    """Verify retry_after is exposed on retryable error classes."""

    def test_rate_limit_error_retry_after(self) -> None:
        response: httpx.Response = _make_response(429)
        exc: RateLimitError = RateLimitError(
            429, response=response, retry_after=2.5
        )
        assert exc.retry_after == 2.5

    def test_service_unavailable_retry_after(self) -> None:
        response: httpx.Response = _make_response(503)
        exc: ServiceUnavailableError = ServiceUnavailableError(
            503, response=response, retry_after=10.0
        )
        assert exc.retry_after == 10.0

    def test_gateway_timeout_retry_after(self) -> None:
        response: httpx.Response = _make_response(504)
        exc: GatewayTimeoutError = GatewayTimeoutError(
            504, response=response, retry_after=15.0
        )
        assert exc.retry_after == 15.0

    def test_retry_after_defaults_to_none(self) -> None:
        response: httpx.Response = _make_response(429)
        exc: RateLimitError = RateLimitError(429, response=response)
        assert exc.retry_after is None


# ---------------------------------------------------------------------------
# Inheritance hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """Verify the exception class hierarchy."""

    def test_knowhere_error_is_base_for_all(self) -> None:
        assert issubclass(APIConnectionError, KnowhereError)
        assert issubclass(APITimeoutError, KnowhereError)
        assert issubclass(PollingTimeoutError, KnowhereError)
        assert issubclass(JobFailedError, KnowhereError)
        assert issubclass(ChecksumError, KnowhereError)
        assert issubclass(APIStatusError, KnowhereError)

    def test_api_status_error_is_base_for_http_errors(self) -> None:
        assert issubclass(BadRequestError, APIStatusError)
        assert issubclass(AuthenticationError, APIStatusError)
        assert issubclass(PaymentRequiredError, APIStatusError)
        assert issubclass(PermissionDeniedError, APIStatusError)
        assert issubclass(NotFoundError, APIStatusError)
        assert issubclass(ConflictError, APIStatusError)
        assert issubclass(RateLimitError, APIStatusError)
        assert issubclass(InternalServerError, APIStatusError)
        assert issubclass(ServiceUnavailableError, APIStatusError)
        assert issubclass(GatewayTimeoutError, APIStatusError)

    def test_api_timeout_is_connection_error(self) -> None:
        assert issubclass(APITimeoutError, APIConnectionError)


# ---------------------------------------------------------------------------
# JobFailedError
# ---------------------------------------------------------------------------


class TestJobFailedError:
    """Verify JobFailedError carries job_result, code, and message."""

    def test_carries_job_result(self) -> None:
        fake_result: Dict[str, str] = {"job_id": "j1", "status": "failed"}
        exc: JobFailedError = JobFailedError(
            job_result=fake_result, code="PARSE_ERROR", message="Could not parse"
        )
        assert exc.job_result == fake_result
        assert exc.code == "PARSE_ERROR"
        assert exc.message == "Could not parse"

    def test_string_representation(self) -> None:
        exc: JobFailedError = JobFailedError(
            job_result=None, code="ERR", message="fail"
        )
        assert "ERR" in str(exc)
        assert "fail" in str(exc)


# ---------------------------------------------------------------------------
# PollingTimeoutError
# ---------------------------------------------------------------------------


class TestPollingTimeoutError:
    """Verify PollingTimeoutError message includes job_id and timeout."""

    def test_message_includes_job_id(self) -> None:
        exc: PollingTimeoutError = PollingTimeoutError(
            job_id="job_abc", elapsed=120.0
        )
        assert "job_abc" in str(exc)

    def test_message_includes_elapsed(self) -> None:
        exc: PollingTimeoutError = PollingTimeoutError(
            job_id="job_abc", elapsed=120.0
        )
        assert "120.0" in str(exc)

    def test_attributes(self) -> None:
        exc: PollingTimeoutError = PollingTimeoutError(
            job_id="job_xyz", elapsed=60.5
        )
        assert exc.job_id == "job_xyz"
        assert exc.elapsed == 60.5


# ---------------------------------------------------------------------------
# ChecksumError
# ---------------------------------------------------------------------------


class TestChecksumError:
    """Verify ChecksumError carries expected and actual values."""

    def test_attributes(self) -> None:
        exc: ChecksumError = ChecksumError(expected="aaa", actual="bbb")
        assert exc.expected == "aaa"
        assert exc.actual == "bbb"
        assert "aaa" in str(exc)
        assert "bbb" in str(exc)
