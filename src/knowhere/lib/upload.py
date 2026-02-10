"""File upload helpers for sync and async clients."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Dict, Optional, Union

import httpx

from knowhere._exceptions import APIConnectionError, APITimeoutError
from knowhere._logging import getLogger
from knowhere._types import UploadProgressCallback

_logger = getLogger()

# Chunk size for streaming uploads (256 KiB)
_UPLOAD_CHUNK_SIZE: int = 256 * 1024


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
) -> None:
    """Upload *file* to *upload_url* using a synchronous PUT request."""
    content, total_bytes = _prepareFileContent(file)
    headers: Dict[str, str] = _buildUploadHeaders(upload_headers, total_bytes)

    _logger.debug("Uploading %s bytes to %s", total_bytes, upload_url)

    if isinstance(content, bytes):
        data: bytes = content
    else:
        # BinaryIO — read all for simplicity (already measured size)
        pos: int = content.tell()
        data = content.read()
        content.seek(pos)

    if on_progress:
        on_progress(0, total_bytes)

    try:
        response: httpx.Response = client.put(
            upload_url,
            content=data,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise APITimeoutError(f"Upload timed out: {exc}") from exc
    except httpx.HTTPError as exc:
        raise APIConnectionError(f"Upload failed: {exc}") from exc

    if on_progress:
        on_progress(len(data), total_bytes)

    _logger.debug("Upload complete: %d", response.status_code)


async def asyncUploadFile(
    client: httpx.AsyncClient,
    upload_url: str,
    upload_headers: Optional[Dict[str, str]],
    file: Union[Path, BinaryIO, bytes],
    on_progress: Optional[UploadProgressCallback] = None,
    *,
    timeout: float = 600.0,
) -> None:
    """Upload *file* to *upload_url* using an async PUT request."""
    content, total_bytes = _prepareFileContent(file)
    headers: Dict[str, str] = _buildUploadHeaders(upload_headers, total_bytes)

    _logger.debug("Async uploading %s bytes to %s", total_bytes, upload_url)

    if isinstance(content, bytes):
        data: bytes = content
    else:
        pos = content.tell()
        data = content.read()
        content.seek(pos)

    if on_progress:
        on_progress(0, total_bytes)

    try:
        response: httpx.Response = await client.put(
            upload_url,
            content=data,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise APITimeoutError(f"Upload timed out: {exc}") from exc
    except httpx.HTTPError as exc:
        raise APIConnectionError(f"Upload failed: {exc}") from exc

    if on_progress:
        on_progress(len(data), total_bytes)

    _logger.debug("Async upload complete: %d", response.status_code)
