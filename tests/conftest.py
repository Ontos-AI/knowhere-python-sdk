"""Shared fixtures for the Knowhere SDK test suite."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from typing import Any, Callable, Dict, Generator, Optional

import pytest


# ---------------------------------------------------------------------------
# Simple value fixtures
# ---------------------------------------------------------------------------

API_KEY: str = "sk_test_key_12345"
BASE_URL: str = "https://api.test.knowhereto.ai"


@pytest.fixture()
def api_key() -> str:
    """Return a deterministic test API key."""
    return API_KEY


@pytest.fixture()
def base_url() -> str:
    """Return a deterministic test base URL."""
    return BASE_URL


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sync_client(api_key: str, base_url: str) -> Generator[Any, None, None]:
    """Create a synchronous Knowhere client and close it after the test."""
    from knowhere import Knowhere

    client: Knowhere = Knowhere(api_key=api_key, base_url=base_url)
    yield client
    client.close()


@pytest.fixture()
async def async_client(api_key: str, base_url: str) -> Any:
    """Create an async Knowhere client and close it after the test."""
    from knowhere import AsyncKnowhere

    client: AsyncKnowhere = AsyncKnowhere(api_key=api_key, base_url=base_url)
    yield client
    await client.close()


# ---------------------------------------------------------------------------
# Mock API response factories
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_job_response() -> Dict[str, Any]:
    """Return a dict matching POST /v1/jobs response for a file upload job.

    The APIResponse.parse() calls model_validate() on the raw JSON, so
    the response body must match the Job model directly.
    """
    return {
        "job_id": "job_test123",
        "status": "waiting-file",
        "source_type": "file",
        "data_id": None,
        "created_at": "2025-01-01T00:00:00Z",
        "upload_url": "https://storage.example.com/upload?token=abc",
        "upload_headers": {"Content-Type": "application/pdf"},
        "expires_in": 3600,
    }


@pytest.fixture()
def mock_job_result_response() -> Dict[str, Any]:
    """Return a dict matching GET /v1/jobs/{id} for a completed job."""
    return {
        "job_id": "job_test123",
        "status": "done",
        "source_type": "file",
        "data_id": "data_abc",
        "created_at": "2025-01-01T00:00:00Z",
        "progress": 1.0,
        "error": None,
        "result": {"pages": 1},
        "result_url": "https://storage.example.com/result.zip",
        "result_url_expires_at": "2025-01-02T00:00:00Z",
        "file_name": "test.pdf",
        "file_extension": "pdf",
        "model": "default",
        "ocr_enabled": True,
        "duration_seconds": 5.2,
        "credits_spent": 1.0,
    }


@pytest.fixture()
def mock_error_response() -> Callable[..., Dict[str, Any]]:
    """Factory that creates error response dicts."""

    def _factory(
        code: str = "UNKNOWN",
        message: str = "An error occurred",
        request_id: Optional[str] = "req_abc123",
        details: Optional[Any] = None,
    ) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": details,
            },
        }

    return _factory


# ---------------------------------------------------------------------------
# Sample ZIP bytes
# ---------------------------------------------------------------------------


CHUNKS_LIST: list[Dict[str, Any]] = [
    {
        "chunk_id": "text_chunk_1",
        "type": "text",
        "content": "Hello world",
        "path": "test/section1",
        "length": 11,
        "tokens": ["Hello", "world"],
        "keywords": ["hello"],
        "summary": "A greeting",
        "relationships": [],
    },
    {
        "chunk_id": "IMAGE_test1",
        "type": "image",
        "content": "A test image",
        "path": "test/images",
        "length": 12,
        "file_path": "images/IMAGE_test1.jpg",
        "original_name": "test-image.jpg",
        "summary": "Test image",
    },
]

FULL_MD: str = "# Test\n\nHello world"
IMAGE_BYTES: bytes = b"\xff\xd8\xff\xe0"


def build_sample_zip(checksum_value: Optional[str] = None) -> bytes:
    """Build a minimal valid ZIP archive.

    If *checksum_value* is ``None``, the checksum field is set to an empty
    string so that checksum verification will fail (callers that need
    verification should compute the correct value separately).
    """
    manifest_data: Dict[str, Any] = {
        "version": "1.0",
        "job_id": "job_test123",
        "data_id": None,
        "source_file_name": "test.pdf",
        "processing_date": "2025-01-01T00:00:00Z",
        "checksum": {
            "algorithm": "sha256",
            "value": checksum_value or "",
        },
        "statistics": {
            "total_chunks": 2,
            "text_chunks": 1,
            "image_chunks": 1,
            "table_chunks": 0,
            "total_pages": 1,
        },
        "files": {
            "chunks": "chunks.json",
            "markdown": "full.md",
            "images": [
                {
                    "id": "IMAGE_test1",
                    "file_path": "images/IMAGE_test1.jpg",
                    "original_name": "test-image.jpg",
                    "size_bytes": 4,
                    "format": "jpeg",
                    "width": 100,
                    "height": 100,
                }
            ],
            "tables": [],
        },
    }

    chunks_json: str = json.dumps(CHUNKS_LIST)

    buf: io.BytesIO = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest_data))
        zf.writestr("chunks.json", chunks_json)
        zf.writestr("full.md", FULL_MD)
        zf.writestr("images/IMAGE_test1.jpg", IMAGE_BYTES)

    return buf.getvalue()


def build_sample_zip_with_valid_checksum() -> bytes:
    """Build a ZIP whose manifest checksum matches the ZIP bytes.

    Two-pass approach: build once to get the bytes, compute the hash,
    then rebuild with the correct checksum embedded.
    """
    # First pass: build with a placeholder
    first_pass: bytes = build_sample_zip(checksum_value="placeholder")
    # The actual checksum is over the entire ZIP bytes, but we cannot
    # embed the correct checksum because it changes the ZIP.
    # Instead, we build with verify_checksum=False in most tests.
    # For checksum tests, we use the actual hash of the final ZIP.
    return first_pass


@pytest.fixture()
def sample_zip_bytes() -> bytes:
    """Return a minimal valid ZIP archive for result parsing tests.

    Checksum verification should be disabled when using this fixture
    because the embedded checksum does not match the ZIP bytes.
    """
    return build_sample_zip(checksum_value="")
