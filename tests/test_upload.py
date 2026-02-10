"""Tests for the upload logic: file types, progress callbacks, error handling."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Any, List, Optional, Tuple

import httpx
import pytest
import respx

from knowhere._exceptions import KnowhereError
from knowhere.types.job import Job


UPLOAD_URL: str = "https://storage.example.com/upload?token=abc"


def _make_job_with_upload_url(upload_url: str) -> Job:
    """Create a Job object with an upload URL."""
    return Job(
        job_id="job_upload_test",
        status="waiting-file",
        source_type="file",
        upload_url=upload_url,
        upload_headers={"Content-Type": "application/pdf"},
    )


# ---------------------------------------------------------------------------
# Upload from Path
# ---------------------------------------------------------------------------


class TestUploadFromPath:
    """Verify upload sends file content via PUT when given a Path."""

    @respx.mock
    def test_upload_path_sends_put(self, sync_client: Any) -> None:
        route = respx.put(UPLOAD_URL).mock(
            return_value=httpx.Response(200)
        )

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"fake pdf content from path")
            tmp_path: Path = Path(tmp.name)

        try:
            job: Job = _make_job_with_upload_url(UPLOAD_URL)
            sync_client.jobs.upload(job, tmp_path)
            assert route.called
        finally:
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Upload from bytes
# ---------------------------------------------------------------------------


class TestUploadFromBytes:
    """Verify upload sends content via PUT when given bytes."""

    @respx.mock
    def test_upload_bytes_sends_put(self, sync_client: Any) -> None:
        route = respx.put(UPLOAD_URL).mock(
            return_value=httpx.Response(200)
        )

        job: Job = _make_job_with_upload_url(UPLOAD_URL)
        sync_client.jobs.upload(job, b"raw bytes content")

        assert route.called


# ---------------------------------------------------------------------------
# Upload from seekable BinaryIO
# ---------------------------------------------------------------------------


class TestUploadFromBinaryIO:
    """Verify upload works with seekable BinaryIO objects."""

    @respx.mock
    def test_upload_seekable_binary_io(self, sync_client: Any) -> None:
        route = respx.put(UPLOAD_URL).mock(
            return_value=httpx.Response(200)
        )

        buffer: io.BytesIO = io.BytesIO(b"binary io content")
        job: Job = _make_job_with_upload_url(UPLOAD_URL)
        sync_client.jobs.upload(job, buffer)

        assert route.called


# ---------------------------------------------------------------------------
# Non-seekable BinaryIO raises on retry
# ---------------------------------------------------------------------------


class TestUploadNonSeekableBinaryIO:
    """Verify non-seekable BinaryIO raises an error on retry."""

    @respx.mock
    def test_non_seekable_raises_on_retry(self, sync_client: Any) -> None:
        """When a non-seekable stream is used and the request fails,
        the SDK should raise an error because it cannot rewind."""
        # First call fails with 503, triggering a retry attempt
        respx.put(UPLOAD_URL).mock(
            side_effect=[
                httpx.Response(503, json={"error": "unavailable"}),
                httpx.Response(200),
            ]
        )

        class NonSeekableIO(io.RawIOBase):
            """A non-seekable binary stream."""

            def __init__(self, data: bytes) -> None:
                self._data: bytes = data
                self._pos: int = 0

            def readable(self) -> bool:
                return True

            def seekable(self) -> bool:
                return False

            def readinto(self, b: bytearray) -> int:
                remaining: bytes = self._data[self._pos:]
                n: int = min(len(b), len(remaining))
                b[:n] = remaining[:n]
                self._pos += n
                return n

        stream: NonSeekableIO = NonSeekableIO(b"non-seekable content")
        job: Job = _make_job_with_upload_url(UPLOAD_URL)

        with pytest.raises((KnowhereError, Exception)):
            sync_client.jobs.upload(job, stream)


# ---------------------------------------------------------------------------
# Upload progress callback
# ---------------------------------------------------------------------------


class TestUploadProgressCallback:
    """Verify on_progress callback is called during upload."""

    @respx.mock
    def test_on_progress_called(self, sync_client: Any) -> None:
        route = respx.put(UPLOAD_URL).mock(
            return_value=httpx.Response(200)
        )

        progress_calls: List[Tuple[int, Optional[int]]] = []

        def on_progress(bytes_sent: int, total: Optional[int]) -> None:
            progress_calls.append((bytes_sent, total))

        job: Job = _make_job_with_upload_url(UPLOAD_URL)
        sync_client.jobs.upload(
            job,
            b"content for progress tracking",
            on_progress=on_progress,
        )

        assert route.called
        # The callback should have been called at least once
        assert len(progress_calls) >= 1


# ---------------------------------------------------------------------------
# Upload with URL string (no Job object)
# ---------------------------------------------------------------------------


class TestUploadWithUrlString:
    """Verify upload works when given a URL string instead of a Job."""

    @respx.mock
    def test_upload_url_string_sends_put(self, sync_client: Any) -> None:
        route = respx.put(UPLOAD_URL).mock(
            return_value=httpx.Response(200)
        )

        sync_client.jobs.upload(UPLOAD_URL, b"content via url string")

        assert route.called
