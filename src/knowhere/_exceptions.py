"""Exception hierarchy for the Knowhere SDK."""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

import httpx


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class KnowhereError(Exception):
    """Root exception for every error raised by the Knowhere SDK."""

    message: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# Connection / timeout
# ---------------------------------------------------------------------------


class APIConnectionError(KnowhereError):
    """Raised when the SDK cannot reach the Knowhere API (DNS, TCP, TLS)."""

    def __init__(self, message: str = "Connection error.") -> None:
        super().__init__(message)


class APITimeoutError(APIConnectionError):
    """Raised when a request exceeds the configured timeout."""

    def __init__(self, message: str = "Request timed out.") -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# Validation / state
# ---------------------------------------------------------------------------


class ValidationError(KnowhereError):
    """Raised when the caller provides invalid arguments."""


class InvalidStateError(KnowhereError):
    """Raised when an object is in an unexpected state for the operation."""


# ---------------------------------------------------------------------------
# Polling / job errors
# ---------------------------------------------------------------------------


class PollingTimeoutError(KnowhereError):
    """Raised when polling for a job result exceeds the configured timeout."""

    job_id: str
    elapsed: float

    def __init__(self, job_id: str, elapsed: float) -> None:
        super().__init__(
            f"Polling for job '{job_id}' timed out after {elapsed:.1f}s."
        )
        self.job_id = job_id
        self.elapsed = elapsed


class JobFailedError(KnowhereError):
    """Raised when a job reaches the ``failed`` terminal status."""

    job_result: Any  # JobResult — forward-ref to avoid circular import
    code: str
    message: str

    def __init__(
        self,
        job_result: Any,
        code: str,
        message: str,
    ) -> None:
        super().__init__(f"Job failed [{code}]: {message}")
        self.job_result = job_result
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------


class ChecksumError(KnowhereError):
    """Raised when the SHA-256 checksum of a downloaded result does not match."""

    expected: str
    actual: str

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(
            f"Checksum mismatch: expected {expected}, got {actual}."
        )
        self.expected = expected
        self.actual = actual


# ---------------------------------------------------------------------------
# HTTP status errors
# ---------------------------------------------------------------------------


class APIStatusError(KnowhereError):
    """Raised for HTTP 4xx / 5xx responses from the Knowhere API."""

    status_code: int
    code: str
    request_id: Optional[str]
    details: Optional[Any]
    body: Optional[Any]
    response: httpx.Response

    def __init__(
        self,
        status_code: int,
        *,
        code: str = "unknown",
        message: str = "Unknown API error",
        request_id: Optional[str] = None,
        details: Optional[Any] = None,
        body: Optional[Any] = None,
        response: httpx.Response,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.request_id = request_id
        self.details = details
        self.body = body
        self.response = response
        super().__init__(
            f"[{status_code}] {code}: {message}"
            + (f" (request_id={request_id})" if request_id else "")
        )


class BadRequestError(APIStatusError):
    """HTTP 400."""


class AuthenticationError(APIStatusError):
    """HTTP 401."""


class PaymentRequiredError(APIStatusError):
    """HTTP 402."""


class PermissionDeniedError(APIStatusError):
    """HTTP 403."""


class NotFoundError(APIStatusError):
    """HTTP 404."""


class ConflictError(APIStatusError):
    """HTTP 409."""


class RateLimitError(APIStatusError):
    """HTTP 429 — includes optional rate limit hints from the server.

    Attributes:
        retry_after: Seconds to wait before retrying (``None`` for quota exceeded).
        limit: Maximum allowed requests in the rate window.
        period: Rate window unit (``"second"``, ``"minute"``, ``"hour"``, ``"day"``).
    """

    retry_after: Optional[float]
    limit: Optional[int]
    period: Optional[str]

    def __init__(
        self,
        status_code: int,
        *,
        code: str = "rate_limit_exceeded",
        message: str = "Rate limit exceeded",
        request_id: Optional[str] = None,
        details: Optional[Any] = None,
        body: Optional[Any] = None,
        response: httpx.Response,
        retry_after: Optional[float] = None,
        limit: Optional[int] = None,
        period: Optional[str] = None,
    ) -> None:
        super().__init__(
            status_code,
            code=code,
            message=message,
            request_id=request_id,
            details=details,
            body=body,
            response=response,
        )
        self.retry_after = retry_after
        self.limit = limit
        self.period = period


class InternalServerError(APIStatusError):
    """HTTP 500."""


class ServiceUnavailableError(APIStatusError):
    """HTTP 502 / 503 — includes optional rate limit hints from the server.

    Attributes:
        retry_after: Seconds to wait before retrying.
        limit: Maximum allowed requests in the rate window (optional).
        period: Rate window unit (optional).
    """

    retry_after: Optional[float]
    limit: Optional[int]
    period: Optional[str]

    def __init__(
        self,
        status_code: int,
        *,
        code: str = "service_unavailable",
        message: str = "Service unavailable",
        request_id: Optional[str] = None,
        details: Optional[Any] = None,
        body: Optional[Any] = None,
        response: httpx.Response,
        retry_after: Optional[float] = None,
        limit: Optional[int] = None,
        period: Optional[str] = None,
    ) -> None:
        super().__init__(
            status_code,
            code=code,
            message=message,
            request_id=request_id,
            details=details,
            body=body,
            response=response,
        )
        self.retry_after = retry_after
        self.limit = limit
        self.period = period


class GatewayTimeoutError(APIStatusError):
    """HTTP 504 — includes optional rate limit hints from the server.

    Attributes:
        retry_after: Seconds to wait before retrying.
        limit: Maximum allowed requests in the rate window (optional).
        period: Rate window unit (optional).
    """

    retry_after: Optional[float]
    limit: Optional[int]
    period: Optional[str]

    def __init__(
        self,
        status_code: int,
        *,
        code: str = "gateway_timeout",
        message: str = "Gateway timeout",
        request_id: Optional[str] = None,
        details: Optional[Any] = None,
        body: Optional[Any] = None,
        response: httpx.Response,
        retry_after: Optional[float] = None,
        limit: Optional[int] = None,
        period: Optional[str] = None,
    ) -> None:
        super().__init__(
            status_code,
            code=code,
            message=message,
            request_id=request_id,
            details=details,
            body=body,
            response=response,
        )
        self.retry_after = retry_after
        self.limit = limit
        self.period = period


# ---------------------------------------------------------------------------
# Status code -> exception class mapping
# ---------------------------------------------------------------------------

_STATUS_TO_EXCEPTION: Dict[int, Type[APIStatusError]] = {
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


def makeStatusError(
    status_code: int,
    response: httpx.Response,
    body: Optional[Any] = None,
) -> APIStatusError:
    """Create the appropriate ``APIStatusError`` subclass for *status_code*.

    If *body* is a dict it is expected to follow the Knowhere error envelope::

        {"error": {"code": "...", "message": "...", "request_id": "...", "details": ...}}
    """
    code: str = "unknown"
    message: str = response.reason_phrase or "Unknown error"
    request_id: Optional[str] = None
    details: Optional[Any] = None

    if isinstance(body, dict):
        error_obj: Any = body.get("error", body)
        if isinstance(error_obj, dict):
            code = error_obj.get("code", code)
            message = error_obj.get("message", message)
            request_id = error_obj.get("request_id", request_id)
            details = error_obj.get("details", details)

    exception_class: Type[APIStatusError] = _STATUS_TO_EXCEPTION.get(
        status_code, APIStatusError
    )

    # Extract retry hints for classes that support them
    # Prefer body: error.details.retry_after, fallback to HTTP header
    retry_after: Optional[float] = None
    limit: Optional[int] = None
    period: Optional[str] = None

    if isinstance(details, dict):
        raw_body_retry: Any = details.get("retry_after")
        if raw_body_retry is not None:
            try:
                retry_after = float(raw_body_retry)
            except (ValueError, TypeError):
                pass
        raw_limit: Any = details.get("limit")
        if raw_limit is not None:
            try:
                limit = int(raw_limit)
            except (ValueError, TypeError):
                pass
        raw_period: Any = details.get("period")
        if isinstance(raw_period, str):
            period = raw_period

    if retry_after is None:
        raw_header_retry: Optional[str] = response.headers.get("retry-after")
        if raw_header_retry is not None:
            try:
                retry_after = float(raw_header_retry)
            except (ValueError, TypeError):
                pass

    common_kwargs: Dict[str, Any] = dict(
        code=code,
        message=message,
        request_id=request_id,
        details=details,
        body=body,
        response=response,
    )

    if exception_class in (RateLimitError, ServiceUnavailableError, GatewayTimeoutError):
        return exception_class(
            status_code,
            **common_kwargs,
            retry_after=retry_after,  # type: ignore[call-arg]
            limit=limit,
            period=period,
        )

    return exception_class(status_code, **common_kwargs)
