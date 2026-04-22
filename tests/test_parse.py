"""Tests for the high-level client.parse() convenience method."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest

from knowhere._exceptions import ValidationError
import respx

from tests.conftest import BASE_URL


JOBS_URL: str = f"{BASE_URL}/v1/jobs"


def _make_create_response(
    job_id: str,
    source_type: str,
    upload_url: str | None = None,
) -> Dict[str, Any]:
    """Build a mock POST /v1/jobs response (raw model data)."""
    return {
        "job_id": job_id,
        "status": "waiting-file" if source_type == "file" else "pending",
        "source_type": source_type,
        "upload_url": upload_url,
        "upload_headers": (
            {"Content-Type": "application/pdf"} if upload_url else None
        ),
        "expires_in": 3600 if upload_url else None,
    }


def _make_done_response(job_id: str, result_url: str) -> Dict[str, Any]:
    """Build a mock GET /v1/jobs/{id} response for a completed job."""
    return {
        "job_id": job_id,
        "status": "done",
        "source_type": "url",
        "namespace": "support-center",
        "document_id": "doc_123",
        "result_url": result_url,
    }


# ---------------------------------------------------------------------------
# parse(url=...)
# ---------------------------------------------------------------------------


class TestParseWithUrl:
    """Verify client.parse(url=...) orchestrates create -> poll -> load."""

    @respx.mock
    def test_parse_url_full_flow(
        self,
        sync_client: Any,
        sample_zip_bytes: bytes,
    ) -> None:
        job_id: str = "job_url_parse"
        result_url: str = "https://storage.example.com/result.zip"

        # Step 1: create job
        respx.post(JOBS_URL).mock(
            return_value=httpx.Response(
                200,
                json=_make_create_response(job_id, "url"),
            )
        )

        # Step 2: poll (returns done immediately)
        respx.get(f"{JOBS_URL}/{job_id}").mock(
            return_value=httpx.Response(
                200,
                json=_make_done_response(job_id, result_url),
            )
        )

        # Step 3: download result
        respx.get(result_url).mock(
            return_value=httpx.Response(
                200,
                content=sample_zip_bytes,
                headers={"Content-Type": "application/zip"},
            )
        )

        parse_result = sync_client.parse(
            url="https://example.com/doc.pdf",
            poll_interval=0.01,
            verify_checksum=False,
        )

        assert parse_result.manifest is not None
        assert parse_result.manifest.job_id == "job_test123"
        assert parse_result.namespace == "support-center"
        assert parse_result.document_id == "doc_123"


# ---------------------------------------------------------------------------
# parse(file=Path(...))
# ---------------------------------------------------------------------------


class TestParseWithFilePath:
    """Verify client.parse(file=Path(...)) does create -> upload -> poll -> load."""

    @respx.mock
    def test_parse_file_path_full_flow(
        self,
        sync_client: Any,
        sample_zip_bytes: bytes,
    ) -> None:
        job_id: str = "job_file_parse"
        upload_url: str = "https://storage.example.com/upload?token=abc"
        result_url: str = "https://storage.example.com/result.zip"

        # Step 1: create job
        respx.post(JOBS_URL).mock(
            return_value=httpx.Response(
                200,
                json=_make_create_response(job_id, "file", upload_url),
            )
        )

        # Step 2: upload file
        respx.put(upload_url).mock(
            return_value=httpx.Response(200)
        )

        # Step 3: poll
        respx.get(f"{JOBS_URL}/{job_id}").mock(
            return_value=httpx.Response(
                200,
                json=_make_done_response(job_id, result_url),
            )
        )

        # Step 4: download result
        respx.get(result_url).mock(
            return_value=httpx.Response(
                200,
                content=sample_zip_bytes,
                headers={"Content-Type": "application/zip"},
            )
        )

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"fake pdf content")
            tmp_path: Path = Path(tmp.name)

        try:
            parse_result = sync_client.parse(
                file=tmp_path,
                poll_interval=0.01,
                verify_checksum=False,
            )
            assert parse_result.manifest is not None
        finally:
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# parse(file=bytes, file_name=...)
# ---------------------------------------------------------------------------


class TestParseWithBytes:
    """Verify client.parse(file=b'...', file_name=...) works correctly."""

    @respx.mock
    def test_parse_bytes_with_file_name(
        self,
        sync_client: Any,
        sample_zip_bytes: bytes,
    ) -> None:
        job_id: str = "job_bytes_parse"
        upload_url: str = "https://storage.example.com/upload?token=def"
        result_url: str = "https://storage.example.com/result.zip"

        respx.post(JOBS_URL).mock(
            return_value=httpx.Response(
                200,
                json=_make_create_response(job_id, "file", upload_url),
            )
        )
        respx.put(upload_url).mock(return_value=httpx.Response(200))
        respx.get(f"{JOBS_URL}/{job_id}").mock(
            return_value=httpx.Response(
                200,
                json=_make_done_response(job_id, result_url),
            )
        )
        respx.get(result_url).mock(
            return_value=httpx.Response(
                200,
                content=sample_zip_bytes,
                headers={"Content-Type": "application/zip"},
            )
        )

        parse_result = sync_client.parse(
            file=b"fake pdf bytes",
            file_name="document.pdf",
            poll_interval=0.01,
            verify_checksum=False,
        )

        assert parse_result.manifest is not None


# ---------------------------------------------------------------------------
# Validation: missing url and file, or both provided
# ---------------------------------------------------------------------------


class TestParseValidation:
    """Verify parse() raises ValueError for invalid argument combinations."""

    def test_missing_url_and_file_raises_value_error(
        self, sync_client: Any
    ) -> None:
        with pytest.raises(ValidationError, match="url.*file|file.*url"):
            sync_client.parse()

    def test_both_url_and_file_raises_value_error(
        self, sync_client: Any
    ) -> None:
        with pytest.raises(ValidationError, match="url.*file|file.*url"):
            sync_client.parse(
                url="https://example.com/doc.pdf",
                file=b"content",
            )
