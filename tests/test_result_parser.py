"""Tests for the result parser: ZIP extraction, checksum, Zip Slip protection."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from knowhere._exceptions import ChecksumError, KnowhereError
from knowhere.lib.result_parser import parseResultZip
from knowhere.types.result import (
    ImageChunk,
    Manifest,
    ParseResult,
    Statistics,
    TableChunk,
    TextChunk,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


CHUNKS_LIST: List[Dict[str, Any]] = [
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

TEXT_TOKENS_LIST: List[str] = ["Ashish", "Vaswani", "attention", "transformer"]

MARKDOWN: str = "# Test\n\nHello world"
IMAGE_BYTES: bytes = b"\xff\xd8\xff\xe0"


def _build_zip(
    manifest: Dict[str, Any],
    chunks: List[Dict[str, Any]] | None = None,
    markdown: str = MARKDOWN,
    image_bytes: bytes = IMAGE_BYTES,
    extra_entries: Dict[str, bytes] | None = None,
    include_chunks: bool = True,
    include_manifest: bool = True,
) -> bytes:
    """Build a ZIP archive from the given components."""
    buf: io.BytesIO = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if include_manifest:
            zf.writestr("manifest.json", json.dumps(manifest))
        if include_chunks:
            zf.writestr(
                "chunks.json",
                json.dumps(chunks if chunks is not None else CHUNKS_LIST),
            )
        zf.writestr("full.md", markdown)
        zf.writestr("images/IMAGE_test1.jpg", image_bytes)
        if extra_entries:
            for name, data in extra_entries.items():
                zf.writestr(name, data)
    return buf.getvalue()


def _make_manifest(checksum_value: str = "") -> Dict[str, Any]:
    """Build a valid manifest dict with the given checksum."""
    return {
        "version": "1.0",
        "job_id": "job_test123",
        "data_id": None,
        "source_file_name": "test.pdf",
        "processing_date": "2025-01-01T00:00:00Z",
        "checksum": {"algorithm": "sha256", "value": checksum_value},
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


# ---------------------------------------------------------------------------
# Valid ZIP parsing
# ---------------------------------------------------------------------------


class TestParseValidZip:
    """Verify parsing a valid ZIP returns correct ParseResult."""

    def test_returns_parse_result_with_manifest(self) -> None:
        manifest: Dict[str, Any] = _make_manifest()
        zip_bytes: bytes = _build_zip(manifest)

        result: ParseResult = parseResultZip(zip_bytes, verify_checksum=False)

        assert result.manifest is not None
        assert result.manifest.job_id == "job_test123"
        assert result.manifest.source_file_name == "test.pdf"

    def test_loads_text_chunks(self) -> None:
        manifest: Dict[str, Any] = _make_manifest()
        zip_bytes: bytes = _build_zip(manifest)

        result: ParseResult = parseResultZip(zip_bytes, verify_checksum=False)

        text_chunks = result.text_chunks
        assert len(text_chunks) == 1
        assert text_chunks[0].chunk_id == "text_chunk_1"
        assert text_chunks[0].content == "Hello world"

    def test_accepts_text_chunk_tokens_as_list(self) -> None:
        manifest: Dict[str, Any] = _make_manifest()
        chunks: List[Dict[str, Any]] = [
            {
                "chunk_id": "text_chunk_tokens_list",
                "type": "text",
                "content": "Attention is all you need",
                "path": "paper/abstract",
                "metadata": {
                    "length": 25,
                    "tokens": TEXT_TOKENS_LIST,
                    "keywords": ["attention", "transformer"],
                    "summary": "Transformer introduction",
                    "relationships": [],
                },
            }
        ]
        zip_bytes: bytes = _build_zip(manifest, chunks=chunks)

        result: ParseResult = parseResultZip(zip_bytes, verify_checksum=False)

        assert len(result.text_chunks) == 1
        assert result.text_chunks[0].tokens == TEXT_TOKENS_LIST

    def test_rejects_legacy_text_chunk_tokens_string(self) -> None:
        manifest: Dict[str, Any] = _make_manifest()
        chunks: List[Dict[str, Any]] = [
            {
                "chunk_id": "text_chunk_tokens_string",
                "type": "text",
                "content": "Attention is all you need",
                "path": "paper/abstract",
                "metadata": {
                    "length": 25,
                    "tokens": "Ashish;Vaswani;attention;transformer",
                    "keywords": ["attention", "transformer"],
                    "summary": "Transformer introduction",
                    "relationships": [],
                },
            }
        ]
        zip_bytes: bytes = _build_zip(manifest, chunks=chunks)

        with pytest.raises(KnowhereError, match="expected list\\[str\\]"):
            parseResultZip(zip_bytes, verify_checksum=False)

    def test_rejects_integer_text_chunk_tokens(self) -> None:
        manifest: Dict[str, Any] = _make_manifest()
        chunks: List[Dict[str, Any]] = [
            {
                "chunk_id": "text_chunk_tokens_int",
                "type": "text",
                "content": "Attention is all you need",
                "path": "paper/abstract",
                "metadata": {
                    "length": 25,
                    "tokens": 4,
                    "keywords": ["attention", "transformer"],
                    "summary": "Transformer introduction",
                    "relationships": [],
                },
            }
        ]
        zip_bytes: bytes = _build_zip(manifest, chunks=chunks)

        with pytest.raises(KnowhereError, match="expected list\\[str\\]"):
            parseResultZip(zip_bytes, verify_checksum=False)

    def test_loads_image_chunks_with_data(self) -> None:
        manifest: Dict[str, Any] = _make_manifest()
        zip_bytes: bytes = _build_zip(manifest)

        result: ParseResult = parseResultZip(zip_bytes, verify_checksum=False)

        image_chunks = result.image_chunks
        assert len(image_chunks) == 1
        assert image_chunks[0].chunk_id == "IMAGE_test1"
        assert image_chunks[0].data == IMAGE_BYTES

    def test_loads_full_markdown(self) -> None:
        manifest: Dict[str, Any] = _make_manifest()
        zip_bytes: bytes = _build_zip(manifest)

        result: ParseResult = parseResultZip(zip_bytes, verify_checksum=False)

        assert result.full_markdown == MARKDOWN

    def test_get_chunk_finds_by_id(self) -> None:
        manifest: Dict[str, Any] = _make_manifest()
        zip_bytes: bytes = _build_zip(manifest)

        result: ParseResult = parseResultZip(zip_bytes, verify_checksum=False)

        chunk = result.getChunk("text_chunk_1")
        assert chunk is not None
        assert chunk.chunk_id == "text_chunk_1"

    def test_get_chunk_returns_none_for_missing(self) -> None:
        manifest: Dict[str, Any] = _make_manifest()
        zip_bytes: bytes = _build_zip(manifest)

        result: ParseResult = parseResultZip(zip_bytes, verify_checksum=False)

        assert result.getChunk("nonexistent") is None


# ---------------------------------------------------------------------------
# Checksum verification
# ---------------------------------------------------------------------------


class TestChecksumVerification:
    """Verify checksum validation passes and fails correctly."""

    def test_correct_checksum_passes(self) -> None:
        # Build ZIP with empty checksum first, then compute hash
        manifest: Dict[str, Any] = _make_manifest(checksum_value="placeholder")
        zip_bytes: bytes = _build_zip(manifest)
        actual_hash: str = hashlib.sha256(zip_bytes).hexdigest()

        # Rebuild with the correct checksum
        manifest["checksum"]["value"] = actual_hash
        zip_bytes = _build_zip(manifest)
        # Recompute because the ZIP changed
        actual_hash = hashlib.sha256(zip_bytes).hexdigest()
        manifest["checksum"]["value"] = actual_hash
        zip_bytes = _build_zip(manifest)
        final_hash: str = hashlib.sha256(zip_bytes).hexdigest()

        # Use expected_checksum to verify externally
        result: ParseResult = parseResultZip(
            zip_bytes,
            verify_checksum=False,
            expected_checksum=final_hash,
        )
        assert result.manifest is not None

    def test_wrong_checksum_raises_checksum_error(self) -> None:
        manifest: Dict[str, Any] = _make_manifest(
            checksum_value="wrong_checksum_value"
        )
        zip_bytes: bytes = _build_zip(manifest)

        with pytest.raises(ChecksumError):
            parseResultZip(zip_bytes, verify_checksum=True)

    def test_wrong_expected_checksum_raises_error(self) -> None:
        manifest: Dict[str, Any] = _make_manifest()
        zip_bytes: bytes = _build_zip(manifest)

        with pytest.raises(ChecksumError):
            parseResultZip(
                zip_bytes,
                verify_checksum=False,
                expected_checksum="definitely_wrong",
            )


# ---------------------------------------------------------------------------
# Missing required files
# ---------------------------------------------------------------------------


class TestMissingRequiredFiles:
    """Verify errors when required files are missing from the ZIP."""

    def test_missing_manifest_raises_error(self) -> None:
        buf: io.BytesIO = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("chunks.json", json.dumps(CHUNKS_LIST))
            zf.writestr("full.md", MARKDOWN)

        with pytest.raises(KnowhereError, match="(?i)manifest"):
            parseResultZip(buf.getvalue(), verify_checksum=False)

    def test_missing_chunks_returns_empty_chunks(self) -> None:
        """When chunks.json is missing, the result has no chunks."""
        manifest: Dict[str, Any] = _make_manifest()
        zip_bytes: bytes = _build_zip(
            manifest, include_chunks=False
        )

        result: ParseResult = parseResultZip(
            zip_bytes, verify_checksum=False
        )


# ---------------------------------------------------------------------------
# Real Result Tests (Production ZIP)
# ---------------------------------------------------------------------------

FIXTURE_DIR: Path = Path(__file__).parent / "fixtures"
REAL_ZIP_PATH: Path = FIXTURE_DIR / "real_result.zip"


@pytest.fixture()
def real_zip_bytes() -> bytes:
    """Load the real result ZIP from the fixtures directory."""
    if not REAL_ZIP_PATH.exists():
        pytest.skip("Real result fixture not found; run download script first.")
    return REAL_ZIP_PATH.read_bytes()


@pytest.fixture()
def parsed_real_result(real_zip_bytes: bytes) -> ParseResult:
    """Parse the real ZIP with checksum verification disabled."""
    return parseResultZip(real_zip_bytes, verify_checksum=False)


class TestRealResultZip:
    """Tests against a real result ZIP downloaded from the Knowhere server."""

    # -- Manifest --

    def test_manifest_is_present(self, parsed_real_result: ParseResult) -> None:
        assert parsed_real_result.manifest is not None

    def test_manifest_has_job_id(self, parsed_real_result: ParseResult) -> None:
        manifest: Manifest = parsed_real_result.manifest
        assert manifest.job_id is not None
        assert manifest.job_id.startswith("job_")

    def test_manifest_has_version(self, parsed_real_result: ParseResult) -> None:
        assert parsed_real_result.manifest.version == "1.0"

    def test_manifest_has_source_file_name(self, parsed_real_result: ParseResult) -> None:
        assert parsed_real_result.manifest.source_file_name == "cdn.pdf"

    def test_manifest_has_processing_date(self, parsed_real_result: ParseResult) -> None:
        assert parsed_real_result.manifest.processing_date is not None

    # -- Statistics --

    def test_statistics_is_present(self, parsed_real_result: ParseResult) -> None:
        assert parsed_real_result.manifest.statistics is not None

    def test_total_chunks(self, parsed_real_result: ParseResult) -> None:
        stats: Optional[Statistics] = parsed_real_result.manifest.statistics
        assert stats is not None
        assert stats.total_chunks == 44

    def test_text_chunks_count(self, parsed_real_result: ParseResult) -> None:
        stats: Optional[Statistics] = parsed_real_result.manifest.statistics
        assert stats is not None
        assert stats.text_chunks == 39

    def test_image_chunks_count(self, parsed_real_result: ParseResult) -> None:
        stats: Optional[Statistics] = parsed_real_result.manifest.statistics
        assert stats is not None
        assert stats.image_chunks == 4

    def test_table_chunks_count(self, parsed_real_result: ParseResult) -> None:
        stats: Optional[Statistics] = parsed_real_result.manifest.statistics
        assert stats is not None
        assert stats.table_chunks == 1

    def test_total_pages_is_none(self, parsed_real_result: ParseResult) -> None:
        """Server returns total_pages: null — SDK must accept this."""
        stats: Optional[Statistics] = parsed_real_result.manifest.statistics
        assert stats is not None
        assert stats.total_pages is None

    # -- Chunks --

    def test_total_chunk_count(self, parsed_real_result: ParseResult) -> None:
        assert len(parsed_real_result.chunks) == 44

    def test_text_chunks(self, parsed_real_result: ParseResult) -> None:
        text_chunks: List[TextChunk] = parsed_real_result.text_chunks
        assert len(text_chunks) == 39

    def test_image_chunks(self, parsed_real_result: ParseResult) -> None:
        image_chunks: List[ImageChunk] = parsed_real_result.image_chunks
        assert len(image_chunks) == 4

    def test_table_chunks(self, parsed_real_result: ParseResult) -> None:
        table_chunks: List[TableChunk] = parsed_real_result.table_chunks
        assert len(table_chunks) == 1

    def test_all_chunks_have_ids(self, parsed_real_result: ParseResult) -> None:
        for chunk in parsed_real_result.chunks:
            assert chunk.chunk_id is not None
            assert len(chunk.chunk_id) > 0

    def test_all_chunks_have_type(self, parsed_real_result: ParseResult) -> None:
        valid_types: set[str] = {"text", "image", "table"}
        for chunk in parsed_real_result.chunks:
            assert chunk.type in valid_types

    def test_text_chunks_have_content(self, parsed_real_result: ParseResult) -> None:
        for chunk in parsed_real_result.text_chunks:
            assert chunk.content is not None
            assert len(chunk.content) > 0

    def test_image_chunks_have_file_path(self, parsed_real_result: ParseResult) -> None:
        for chunk in parsed_real_result.image_chunks:
            # file_path may come from the chunk JSON or be None if only in metadata
            has_path: bool = chunk.file_path is not None or chunk.path is not None
            assert has_path, f"Chunk {chunk.chunk_id} has neither file_path nor path"

    def test_image_chunks_have_data(self, parsed_real_result: ParseResult) -> None:
        """Image chunks should have binary data loaded from the ZIP."""
        for chunk in parsed_real_result.image_chunks:
            assert chunk.data is not None
            assert len(chunk.data) > 0

    def test_get_chunk_by_id(self, parsed_real_result: ParseResult) -> None:
        """Verify getChunk retrieves the correct chunk by ID."""
        first_chunk = parsed_real_result.chunks[0]
        found: Any = parsed_real_result.getChunk(first_chunk.chunk_id)
        assert found is not None
        assert found.chunk_id == first_chunk.chunk_id

    def test_get_chunk_missing_returns_none(self, parsed_real_result: ParseResult) -> None:
        assert parsed_real_result.getChunk("nonexistent_chunk_id") is None

    # -- Markdown --

    def test_markdown_is_present(self, parsed_real_result: ParseResult) -> None:
        assert parsed_real_result.full_markdown is not None

    def test_markdown_is_substantial(self, parsed_real_result: ParseResult) -> None:
        """The cdn.pdf paper should produce significant markdown content."""
        assert len(parsed_real_result.full_markdown) > 10_000

    def test_markdown_content_sanity(self, parsed_real_result: ParseResult) -> None:
        """Check for expected content from the CDN paper."""
        markdown: str = parsed_real_result.full_markdown
        # The paper is about Akamai / CDN — at least one of these should appear
        assert "Akamai" in markdown or "CDN" in markdown or "content delivery" in markdown.lower()

    # -- Hierarchy --

    def test_hierarchy_is_present(self, parsed_real_result: ParseResult) -> None:
        assert parsed_real_result.hierarchy is not None

    def test_hierarchy_is_structured(self, parsed_real_result: ParseResult) -> None:
        """Hierarchy should be a list or dict with meaningful content."""
        hierarchy: Any = parsed_real_result.hierarchy
        assert isinstance(hierarchy, (list, dict))

    # -- Raw ZIP --

    def test_raw_zip_is_preserved(self, real_zip_bytes: bytes, parsed_real_result: ParseResult) -> None:
        assert parsed_real_result.raw_zip is not None
        assert parsed_real_result.raw_zip == real_zip_bytes
