"""Base HTTP client classes for the Knowhere SDK.

Provides ``BaseClient`` (shared config), ``SyncAPIClient`` (httpx.Client),
and ``AsyncAPIClient`` (httpx.AsyncClient) with retry logic and error handling.
"""

from __future__ import annotations

import os
import random
import time
from typing import Any, Dict, Optional, Type, TypeVar

import httpx

from knowhere._constants import (
    API_VERSION,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_UPLOAD_TIMEOUT,
    ENV_API_KEY,
    ENV_BASE_URL,
)
from knowhere._exceptions import (
    APIConnectionError,
    APITimeoutError,
    ValidationError,
    makeStatusError,
)
from knowhere._logging import getLogger, redactSensitiveHeaders
from knowhere._response import APIResponse
from knowhere._version import __version__

T = TypeVar("T")

_logger = getLogger()

# Error codes that are always safe to retry (matches server ALWAYS_RETRYABLE_ERROR_CODES)
_ALWAYS_RETRYABLE_ERROR_CODES: frozenset[str] = frozenset({
    "ABORTED",            # 409 - Concurrency conflict
    "UNAVAILABLE",        # 503 - Service temporarily down
    "DEADLINE_EXCEEDED",  # 504 - Timeout
})

# RESOURCE_EXHAUSTED (429) is conditionally retryable:
#   - Rate limit: details.retry_after present → RETRY
#   - Quota exceeded: no retry_after → DO NOT RETRY
_CONDITIONALLY_RETRYABLE_ERROR_CODE: str = "RESOURCE_EXHAUSTED"

# HTTP status codes that are always safe to retry
_ALWAYS_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({409, 502, 503, 504})

# HTTP status code that is conditionally retryable (only with retry_after)
_CONDITIONALLY_RETRYABLE_STATUS_CODE: int = 429


class BaseClient:
    """Shared configuration and helper methods for sync/async clients."""

    api_key: str
    base_url: str
    timeout: float
    upload_timeout: float
    max_retries: int
    _default_headers: Dict[str, str]

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        upload_timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        # Resolve: arg > env > default
        resolved_key: Optional[str] = api_key or os.environ.get(ENV_API_KEY)
        if not resolved_key:
            raise ValidationError(
                "An API key must be provided via the 'api_key' argument "
                f"or the {ENV_API_KEY} environment variable."
            )
        self.api_key = resolved_key
        self.base_url = (
            base_url
            or os.environ.get(ENV_BASE_URL)
            or DEFAULT_BASE_URL
        ).rstrip("/")
        self.timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
        self.upload_timeout = (
            upload_timeout if upload_timeout is not None else DEFAULT_UPLOAD_TIMEOUT
        )
        self.max_retries = (
            max_retries if max_retries is not None else DEFAULT_MAX_RETRIES
        )
        self._default_headers = default_headers or {}

    def _buildHeaders(self) -> Dict[str, str]:
        """Return headers including auth and user-agent."""
        headers: Dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": f"knowhere-python/{__version__}",
            "Accept": "application/json",
        }
        headers.update(self._default_headers)
        return headers

    def _buildRequestUrl(self, path: str) -> str:
        """Join ``base_url`` with *path*, inserting the API version prefix."""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        clean_path: str = path.lstrip("/")
        if not clean_path.startswith(API_VERSION):
            clean_path = f"{API_VERSION}/{clean_path}"
        return f"{self.base_url}/{clean_path}"

    def _parseErrorResponse(
        self, response: httpx.Response
    ) -> Optional[Dict[str, Any]]:
        """Try to parse a JSON error body; return ``None`` on failure."""
        try:
            return response.json()  # type: ignore[no-any-return]
        except Exception:
            return None

    def _shouldRetry(
        self,
        status_code: int,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Decide whether a request should be retried.

        Follows server-side retry semantics:
        - ABORTED, UNAVAILABLE, DEADLINE_EXCEEDED → always retry
        - RESOURCE_EXHAUSTED (429) → retry only if details.retry_after present
        - All other errors → never retry
        """
        if error_code:
            if error_code in _ALWAYS_RETRYABLE_ERROR_CODES:
                return True
            if error_code == _CONDITIONALLY_RETRYABLE_ERROR_CODE:
                return self._hasRetryAfter(details)
            return False

        # Fallback to status code when error_code is unavailable
        if status_code in _ALWAYS_RETRYABLE_STATUS_CODES:
            return True
        if status_code == _CONDITIONALLY_RETRYABLE_STATUS_CODE:
            return self._hasRetryAfter(details)
        return False

    @staticmethod
    def _hasRetryAfter(details: Optional[Dict[str, Any]]) -> bool:
        """Check if details contains a retry_after hint."""
        if not isinstance(details, dict):
            return False
        retry_after: Any = details.get("retry_after")
        return retry_after is not None

    @staticmethod
    def _extractRetryAfter(
        error_body: Optional[Dict[str, Any]],
        response: httpx.Response,
    ) -> Optional[float]:
        """Extract retry_after from the response body or Retry-After header.

        The server puts retry_after in ``error.details.retry_after``.
        Falls back to the HTTP ``Retry-After`` header.
        """
        # Prefer body: error.details.retry_after
        if isinstance(error_body, dict):
            err_obj: Any = error_body.get("error", error_body)
            if isinstance(err_obj, dict):
                details: Any = err_obj.get("details")
                if isinstance(details, dict):
                    raw: Any = details.get("retry_after")
                    if raw is not None:
                        try:
                            return float(raw)
                        except (ValueError, TypeError):
                            pass

        # Fallback: HTTP Retry-After header
        header_raw: Optional[str] = response.headers.get("retry-after")
        if header_raw is not None:
            try:
                return float(header_raw)
            except (ValueError, TypeError):
                pass
        return None

    def _calculateRetryDelay(
        self,
        attempt: int,
        retry_after: Optional[float] = None,
    ) -> float:
        """Exponential backoff with jitter, respecting ``Retry-After``."""
        if retry_after is not None and retry_after > 0:
            return retry_after
        # Exponential backoff: 0.5 * 2^attempt, capped at 30s
        base_delay: float = min(0.5 * (2 ** attempt), 30.0)
        jitter: float = random.uniform(0, base_delay * 0.25)
        return base_delay + jitter


# ---------------------------------------------------------------------------
# Synchronous client
# ---------------------------------------------------------------------------


class SyncAPIClient(BaseClient):
    """Synchronous HTTP client backed by ``httpx.Client``."""

    _client: httpx.Client

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        upload_timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            upload_timeout=upload_timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._client = httpx.Client(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
        )

    # -- request with retry loop --

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        cast_to: Type[T],
        headers: Optional[Dict[str, str]] = None,
    ) -> T:
        """Execute an HTTP request with automatic retries and error handling."""
        url: str = self._buildRequestUrl(path)
        request_headers: Dict[str, str] = self._buildHeaders()
        if headers:
            request_headers.update(headers)

        effective_timeout: float = timeout if timeout is not None else self.timeout

        _logger.debug(
            "Request: %s %s headers=%s",
            method,
            url,
            redactSensitiveHeaders(request_headers),
        )

        for attempt in range(self.max_retries + 1):
            try:
                response: httpx.Response = self._client.request(
                    method,
                    url,
                    json=body,
                    params=params,
                    headers=request_headers,
                    timeout=effective_timeout,
                )
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    delay: float = self._calculateRetryDelay(attempt)
                    _logger.warning(
                        "Timeout on attempt %d/%d, retrying in %.1fs",
                        attempt + 1,
                        self.max_retries + 1,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                raise APITimeoutError(
                    f"Request to {url} timed out after {effective_timeout}s."
                ) from exc
            except httpx.HTTPError as exc:
                if attempt < self.max_retries:
                    delay = self._calculateRetryDelay(attempt)
                    _logger.warning(
                        "Connection error on attempt %d/%d, retrying in %.1fs",
                        attempt + 1,
                        self.max_retries + 1,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                raise APIConnectionError(str(exc)) from exc

            _logger.debug(
                "Response: %d %s", response.status_code, url
            )

            # Success
            if response.is_success:
                api_response: APIResponse[T] = APIResponse(
                    response, cast_to
                )
                return api_response.parse()

            # Error — decide whether to retry
            error_body: Optional[Dict[str, Any]] = self._parseErrorResponse(
                response
            )
            error_code: Optional[str] = None
            error_details: Optional[Dict[str, Any]] = None
            if isinstance(error_body, dict):
                err_obj: Any = error_body.get("error", error_body)
                if isinstance(err_obj, dict):
                    error_code = err_obj.get("code")
                    raw_details: Any = err_obj.get("details")
                    if isinstance(raw_details, dict):
                        error_details = raw_details

            if (
                attempt < self.max_retries
                and self._shouldRetry(
                    response.status_code, error_code, error_details
                )
            ):
                retry_after_val: Optional[float] = self._extractRetryAfter(
                    error_body, response
                )
                delay = self._calculateRetryDelay(attempt, retry_after_val)
                _logger.warning(
                    "Retryable error %d on attempt %d/%d, retrying in %.1fs",
                    response.status_code,
                    attempt + 1,
                    self.max_retries + 1,
                    delay,
                )
                time.sleep(delay)
                continue

            raise makeStatusError(response.status_code, response, error_body)

        # Should not reach here, but satisfy the type checker
        raise APIConnectionError("Max retries exceeded.")

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> SyncAPIClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Asynchronous client
# ---------------------------------------------------------------------------


class AsyncAPIClient(BaseClient):
    """Asynchronous HTTP client backed by ``httpx.AsyncClient``."""

    _client: httpx.AsyncClient

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        upload_timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            upload_timeout=upload_timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        cast_to: Type[T],
        headers: Optional[Dict[str, str]] = None,
    ) -> T:
        """Execute an async HTTP request with automatic retries."""
        import asyncio

        url: str = self._buildRequestUrl(path)
        request_headers: Dict[str, str] = self._buildHeaders()
        if headers:
            request_headers.update(headers)

        effective_timeout: float = timeout if timeout is not None else self.timeout

        _logger.debug(
            "Async request: %s %s headers=%s",
            method,
            url,
            redactSensitiveHeaders(request_headers),
        )

        for attempt in range(self.max_retries + 1):
            try:
                response: httpx.Response = await self._client.request(
                    method,
                    url,
                    json=body,
                    params=params,
                    headers=request_headers,
                    timeout=effective_timeout,
                )
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    delay: float = self._calculateRetryDelay(attempt)
                    _logger.warning(
                        "Timeout on attempt %d/%d, retrying in %.1fs",
                        attempt + 1, self.max_retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise APITimeoutError(
                    f"Request to {url} timed out after {effective_timeout}s."
                ) from exc
            except httpx.HTTPError as exc:
                if attempt < self.max_retries:
                    delay = self._calculateRetryDelay(attempt)
                    _logger.warning(
                        "Connection error on attempt %d/%d, retrying in %.1fs",
                        attempt + 1, self.max_retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise APIConnectionError(str(exc)) from exc

            _logger.debug("Async response: %d %s", response.status_code, url)

            if response.is_success:
                api_response: APIResponse[T] = APIResponse(response, cast_to)
                return api_response.parse()

            error_body: Optional[Dict[str, Any]] = self._parseErrorResponse(response)
            error_code: Optional[str] = None
            error_details: Optional[Dict[str, Any]] = None
            if isinstance(error_body, dict):
                err_obj: Any = error_body.get("error", error_body)
                if isinstance(err_obj, dict):
                    error_code = err_obj.get("code")
                    raw_details: Any = err_obj.get("details")
                    if isinstance(raw_details, dict):
                        error_details = raw_details

            if (
                attempt < self.max_retries
                and self._shouldRetry(
                    response.status_code, error_code, error_details
                )
            ):
                retry_after_val: Optional[float] = self._extractRetryAfter(
                    error_body, response
                )
                delay = self._calculateRetryDelay(attempt, retry_after_val)
                _logger.warning(
                    "Retryable error %d on attempt %d/%d, retrying in %.1fs",
                    response.status_code, attempt + 1, self.max_retries + 1, delay,
                )
                await asyncio.sleep(delay)
                continue

            raise makeStatusError(response.status_code, response, error_body)

        raise APIConnectionError("Max retries exceeded.")

    async def close(self) -> None:
        """Close the underlying async HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> AsyncAPIClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
