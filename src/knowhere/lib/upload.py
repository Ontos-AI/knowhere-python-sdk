"""File upload helpers for sync and async clients."""

from __future__ import annotations

import asyncio
import random
import time
from pathlib import Path
from typing import BinaryIO, Dict, Optional, Union

import httpx

from knowhere._constants import DEFAULT_UPLOAD_MAX_RETRIES
from knowhere._exceptions import APIConnectionError, APITimeoutError
from knowhere._logging import getLogger
from knowhere._types import UploadProgressCallback

_logger = getLogger()

# Chunk size for streaming uploads (256 KiB)
_UPLOAD_CHUNK_SIZE: int = 256 * 1024

# Storage-provider HTTP status codes that are safe to retry.
# These are transient errors from S3/GCS/Azure Blob, not Knowhere API codes.
_UPLOAD_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({500, 502, 503, 504})


def _calculateUploadRetryDelay(attempt: int) -> float:
    """Exponential backoff with jitter for upload retries."""
    base_delay: float = min(1.0 * (2 ** attempt), 16.0)
    jitter: float = random.uniform(0, base_delay * 0.25)
    return base_delay + jitter


def _isRetryableUploadError(exc: Exception) -> bool:
    """Return True if the upload error is transient and worth retrying."""
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _UPLOAD_RETRYABLE_STATUS_CODES
    return False


def _prepareFileContent(
    file: Union[Path, BinaryIO, bytes],
) -> tuple[Union[bytes, BinaryIO], Optional[int]]:
    """Normalise *file* into a readable form and return (content, total_bytes).

    For retry safety:
    * ``Path`` — will be re-opened on each attempt by the caller.
    * ``bytes`` — reusable as-is.
    * Seekable ``BinaryIO`` — caller will ``seek(0)`` before each attempt.
    * Non-seekable ``BinaryIO`` — read into bytes once.
    """
    if isinstance(file, Path):
        size: int = file.stat().st_size
        return file.read_bytes(), size
    if isinstance(file, bytes):
        return file, len(file)
    # BinaryIO
    if hasattr(file, "seek") and hasattr(file, "tell"):
        current: int = file.tell()
        file.seek(0, 2)  # seek to end
        size = file.tell()
        file.seek(current)  # restore
        return file, size
    # Non-seekable — read all
    data: bytes = file.read()
    return data, len(data)


def _buildUploadHeaders(
    upload_headers: Optional[Dict[str, str]],
    total_bytes: Optional[int],
) -> Dict[str, str]:
    """Merge upload headers with content-length if known."""
    headers: Dict[str, str] = dict(upload_headers or {})
    if total_bytes is not None and "content-length" not in {
        k.lower() for k in headers
    }:
        headers["Content-Length"] = str(total_bytes)
    return headers


def syncUploadFile(
    client: httpx.Client,
    upload_url: str,
    upload_headers: Optional[Dict[str, str]],
    file: Union[Path, BinaryIO, bytes],
    on_progress: Optional[UploadProgressCallback] = None,
    *,
    timeout: float = 600.0,
    max_retries: int = DEFAULT_UPLOAD_MAX_RETRIES,
) -> None:
    """Upload *file* to *upload_url* using a synchronous PUT request.

    Retries on connection errors, timeouts, and transient storage HTTP errors
    (500/502/503/504) up to *max_retries* times.
    """
    content, total_bytes = _prepareFileContent(file)
    headers: Dict[str, str] = _buildUploadHeaders(upload_headers, total_bytes)

    if isinstance(content, bytes):
        data: bytes = content
    else:
        pos: int = content.tell()
        data = content.read()
        content.seek(pos)

    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        _logger.debug(
            "Upload attempt %d/%d — %s bytes to %s",
            attempt + 1, max_retries + 1, total_bytes, upload_url,
        )

        if on_progress and attempt == 0:
            on_progress(0, total_bytes)

        try:
            response: httpx.Response = client.put(
                upload_url,
                content=data,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < max_retries and _isRetryableUploadError(exc):
                delay: float = _calculateUploadRetryDelay(attempt)
                _logger.warning(
                    "Upload attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt + 1, max_retries + 1, exc, delay,
                )
                time.sleep(delay)
                continue
            # Non-retryable or exhausted retries
            if isinstance(exc, httpx.TimeoutException):
                raise APITimeoutError(f"Upload timed out: {exc}") from exc
            raise APIConnectionError(f"Upload failed: {exc}") from exc

        # Success
        if on_progress:
            on_progress(len(data), total_bytes)
        _logger.debug("Upload complete: %d", response.status_code)
        return

    # Should not reach here, but guard against it
    if last_exc is not None:
        if isinstance(last_exc, httpx.TimeoutException):
            raise APITimeoutError(f"Upload timed out: {last_exc}") from last_exc
        raise APIConnectionError(f"Upload failed: {last_exc}") from last_exc


async def asyncUploadFile(
    client: httpx.AsyncClient,
    upload_url: str,
    upload_headers: Optional[Dict[str, str]],
    file: Union[Path, BinaryIO, bytes],
    on_progress: Optional[UploadProgressCallback] = None,
    *,
    timeout: float = 600.0,
    max_retries: int = DEFAULT_UPLOAD_MAX_RETRIES,
) -> None:
    """Upload *file* to *upload_url* using an async PUT request.

    Retries on connection errors, timeouts, and transient storage HTTP errors
    (500/502/503/504) up to *max_retries* times.
    """
    content, total_bytes = _prepareFileContent(file)
    headers: Dict[str, str] = _buildUploadHeaders(upload_headers, total_bytes)

    if isinstance(content, bytes):
        data: bytes = content
    else:
        pos: int = content.tell()
        data = content.read()
        content.seek(pos)

    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        _logger.debug(
            "Async upload attempt %d/%d — %s bytes to %s",
            attempt + 1, max_retries + 1, total_bytes, upload_url,
        )

        if on_progress and attempt == 0:
            on_progress(0, total_bytes)

        try:
            response: httpx.Response = await client.put(
                upload_url,
                content=data,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < max_retries and _isRetryableUploadError(exc):
                delay: float = _calculateUploadRetryDelay(attempt)
                _logger.warning(
                    "Async upload attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt + 1, max_retries + 1, exc, delay,
                )
                await asyncio.sleep(delay)
                continue
            if isinstance(exc, httpx.TimeoutException):
                raise APITimeoutError(f"Upload timed out: {exc}") from exc
            raise APIConnectionError(f"Upload failed: {exc}") from exc

        if on_progress:
            on_progress(len(data), total_bytes)
        _logger.debug("Async upload complete: %d", response.status_code)
        return

    if last_exc is not None:
        if isinstance(last_exc, httpx.TimeoutException):
            raise APITimeoutError(f"Upload timed out: {last_exc}") from last_exc
        raise APIConnectionError(f"Upload failed: {last_exc}") from last_exc
