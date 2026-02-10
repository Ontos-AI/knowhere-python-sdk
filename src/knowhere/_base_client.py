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
    makeStatusError,
)
from knowhere._logging import getLogger, redactSensitiveHeaders
from knowhere._response import APIResponse
from knowhere._version import __version__

T = TypeVar("T")

_logger = getLogger()

# Error codes that are safe to retry
_RETRYABLE_ERROR_CODES: frozenset[str] = frozenset({
    "rate_limit_exceeded",
    "service_unavailable",
    "gateway_timeout",
    "internal_server_error",
    "timeout",
})

# Status codes that are safe to retry
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})


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
            raise ValueError(
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
        details: Optional[Any] = None,
    ) -> bool:
        """Decide whether a request should be retried."""
        if error_code and error_code in _RETRYABLE_ERROR_CODES:
            return True
        return status_code in _RETRYABLE_STATUS_CODES

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
            if isinstance(error_body, dict):
                err_obj: Any = error_body.get("error", error_body)
                if isinstance(err_obj, dict):
                    error_code = err_obj.get("code")

            if (
                attempt < self.max_retries
                and self._shouldRetry(response.status_code, error_code)
            ):
                retry_after_raw: Optional[str] = response.headers.get(
                    "retry-after"
                )
                retry_after_val: Optional[float] = None
                if retry_after_raw:
                    try:
                        retry_after_val = float(retry_after_raw)
                    except (ValueError, TypeError):
                        pass
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
            if isinstance(error_body, dict):
                err_obj: Any = error_body.get("error", error_body)
                if isinstance(err_obj, dict):
                    error_code = err_obj.get("code")

            if (
                attempt < self.max_retries
                and self._shouldRetry(response.status_code, error_code)
            ):
                retry_after_raw: Optional[str] = response.headers.get("retry-after")
                retry_after_val: Optional[float] = None
                if retry_after_raw:
                    try:
                        retry_after_val = float(retry_after_raw)
                    except (ValueError, TypeError):
                        pass
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
