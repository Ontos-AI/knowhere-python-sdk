"""Tests for Pydantic models: Job, JobResult, Manifest, Statistics, chunks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from knowhere.types.job import Job, JobError, JobResult
from knowhere.types.result import (
    BaseChunk,
    Checksum,
    Chunk,
    FileIndex,
    ImageChunk,
    ImageFileInfo,
    Manifest,
    ParseResult,
    ProcessingCost,
    ProcessingMetadata,
    ProcessingTiming,
    SlimChunk,
    Statistics,
    TableChunk,
    TableFileInfo,
    TextChunk,
)


# ---------------------------------------------------------------------------
# Job model
# ---------------------------------------------------------------------------


class TestJobModel:
    """Verify Job model serialization and deserialization."""

    def test_from_dict_minimal(self) -> None:
        data: Dict[str, Any] = {
            "job_id": "job_1",
            "status": "pending",
            "source_type": "url",
        }
        job: Job = Job(**data)
        assert job.job_id == "job_1"
        assert job.status == "pending"
        assert job.source_type == "url"
        assert job.upload_url is None

    def test_from_dict_with_upload(self) -> None:
        data: Dict[str, Any] = {
            "job_id": "job_2",
            "status": "waiting-file",
            "source_type": "file",
            "upload_url": "https://storage.example.com/upload",
            "upload_headers": {"Content-Type": "application/pdf"},
            "expires_in": 3600,
        }
        job: Job = Job(**data)
        assert job.upload_url == "https://storage.example.com/upload"
        assert job.upload_headers == {"Content-Type": "application/pdf"}
        assert job.expires_in == 3600

    def test_serialization_round_trip(self) -> None:
        data: Dict[str, Any] = {
            "job_id": "job_3",
            "status": "pending",
            "source_type": "url",
            "data_id": "data_abc",
            "created_at": "2025-01-01T00:00:00Z",
        }
        job: Job = Job(**data)
        dumped: Dict[str, Any] = job.model_dump()
        assert dumped["job_id"] == "job_3"
        assert dumped["data_id"] == "data_abc"


# ---------------------------------------------------------------------------
# JobResult model
# ---------------------------------------------------------------------------


class TestJobResultModel:
    """Verify JobResult model and its computed properties."""

    def _make_result(self, status: str) -> JobResult:
        return JobResult(
            job_id="job_test",
            status=status,
            source_type="url",
        )

    def test_done_is_terminal(self) -> None:
        result: JobResult = self._make_result("done")
        assert result.is_terminal is True

    def test_done_is_done(self) -> None:
        result: JobResult = self._make_result("done")
        assert result.is_done is True

    def test_done_is_not_failed(self) -> None:
        result: JobResult = self._make_result("done")
        assert result.is_failed is False

    def test_failed_is_terminal(self) -> None:
        result: JobResult = self._make_result("failed")
        assert result.is_terminal is True

    def test_failed_is_not_done(self) -> None:
        result: JobResult = self._make_result("failed")
        assert result.is_done is False

    def test_failed_is_failed(self) -> None:
        result: JobResult = self._make_result("failed")
        assert result.is_failed is True

    def test_running_is_not_terminal(self) -> None:
        result: JobResult = self._make_result("running")
        assert result.is_terminal is False

    def test_pending_is_not_terminal(self) -> None:
        result: JobResult = self._make_result("pending")
        assert result.is_terminal is False

    def test_waiting_file_is_not_terminal(self) -> None:
        result: JobResult = self._make_result("waiting-file")
        assert result.is_terminal is False

    def test_converting_is_not_terminal(self) -> None:
        result: JobResult = self._make_result("converting")
        assert result.is_terminal is False

    def test_with_error_field(self) -> None:
        result: JobResult = JobResult(
            job_id="job_err",
            status="failed",
            source_type="url",
            error=JobError(
                code="PARSE_ERROR",
                message="Could not parse document",
                request_id="req_1",
            ),
        )
        assert result.error is not None
        assert result.error.code == "PARSE_ERROR"
        assert result.error.message == "Could not parse document"

    def test_with_result_url(self) -> None:
        result: JobResult = JobResult(
            job_id="job_ok",
            status="done",
            source_type="file",
            result_url="https://storage.example.com/result.zip",
            duration_seconds=3.5,
            credits_spent=1.0,
        )
        assert result.result_url == "https://storage.example.com/result.zip"
        assert result.duration_seconds == 3.5


# ---------------------------------------------------------------------------
# JobError model
# ---------------------------------------------------------------------------


class TestJobErrorModel:
    """Verify JobError model."""

    def test_from_dict(self) -> None:
        data: Dict[str, Any] = {
            "code": "INTERNAL_ERROR",
            "message": "Something went wrong",
            "request_id": "req_abc",
            "details": {"trace": "xyz"},
        }
        error: JobError = JobError(**data)
        assert error.code == "INTERNAL_ERROR"
        assert error.message == "Something went wrong"
        assert error.request_id == "req_abc"
        assert error.details == {"trace": "xyz"}

    def test_optional_fields_default_to_none(self) -> None:
        error: JobError = JobError(code="ERR", message="fail")
        assert error.request_id is None
        assert error.details is None


# ---------------------------------------------------------------------------
# Manifest model
# ---------------------------------------------------------------------------


class TestManifestModel:
    """Verify Manifest model from dict."""

    def test_from_dict(self) -> None:
        data: Dict[str, Any] = {
            "version": "1.0",
            "job_id": "job_test123",
            "data_id": None,
            "source_file_name": "test.pdf",
            "processing_date": "2025-01-01T00:00:00Z",
            "checksum": {"algorithm": "sha256", "value": "abc123"},
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
                        "id": "IMG_1",
                        "file_path": "images/IMG_1.jpg",
                        "original_name": "photo.jpg",
                        "size_bytes": 1024,
                        "format": "jpeg",
                        "width": 800,
                        "height": 600,
                    }
                ],
                "tables": [],
            },
        }
        manifest: Manifest = Manifest(**data)
        assert manifest.version == "1.0"
        assert manifest.job_id == "job_test123"
        assert manifest.source_file_name == "test.pdf"
        assert manifest.checksum is not None
        assert manifest.checksum.algorithm == "sha256"
        assert manifest.checksum.value == "abc123"

    def test_statistics_accessible(self) -> None:
        manifest: Manifest = Manifest(
            statistics=Statistics(
                total_chunks=5,
                text_chunks=3,
                image_chunks=1,
                table_chunks=1,
                total_pages=2,
            )
        )
        assert manifest.statistics is not None
        assert manifest.statistics.total_chunks == 5
        assert manifest.statistics.text_chunks == 3

    def test_files_index(self) -> None:
        manifest: Manifest = Manifest(
            files=FileIndex(
                chunks="chunks.json",
                markdown="full.md",
                images=[
                    ImageFileInfo(id="IMG_1", file_path="images/IMG_1.jpg")
                ],
                tables=[
                    TableFileInfo(id="TBL_1", file_path="tables/TBL_1.csv")
                ],
            )
        )
        assert manifest.files is not None
        assert manifest.files.chunks == "chunks.json"
        assert len(manifest.files.images) == 1
        assert len(manifest.files.tables) == 1

    def test_optional_fields_default_to_none(self) -> None:
        manifest: Manifest = Manifest()
        assert manifest.version is None
        assert manifest.job_id is None
        assert manifest.checksum is None
        assert manifest.statistics is None
        assert manifest.files is None

    def test_processing_metadata(self) -> None:
        manifest: Manifest = Manifest(
            version="2.0",
            processing=ProcessingMetadata(
                page_count=12,
                billing_status="charged",
                cost=ProcessingCost(micro_dollars=60000, credits=0.06),
                timing=ProcessingTiming(
                    started_at="2026-04-09T08:20:56.634Z",
                    completed_at="2026-04-09T08:21:12.288Z",
                    duration_ms=15653,
                ),
            ),
        )
        assert manifest.processing is not None
        assert manifest.processing.page_count == 12
        assert manifest.processing.cost is not None
        assert manifest.processing.cost.micro_dollars == 60000
        assert manifest.processing.timing is not None
        assert manifest.processing.timing.duration_ms == 15653


# ---------------------------------------------------------------------------
# Statistics model
# ---------------------------------------------------------------------------


class TestStatisticsModel:
    """Verify Statistics model."""

    def test_from_dict(self) -> None:
        stats: Statistics = Statistics(
            total_chunks=10,
            text_chunks=6,
            image_chunks=3,
            table_chunks=1,
            total_pages=5,
        )
        assert stats.total_chunks == 10
        assert stats.total_pages == 5

    def test_defaults_to_zero(self) -> None:
        stats: Statistics = Statistics()
        assert stats.total_chunks == 0
        assert stats.text_chunks == 0
        assert stats.image_chunks == 0
        assert stats.table_chunks == 0
        assert stats.total_pages == 0


# ---------------------------------------------------------------------------
# Checksum model
# ---------------------------------------------------------------------------


class TestChecksumModel:
    """Verify Checksum model."""

    def test_from_dict(self) -> None:
        checksum: Checksum = Checksum(algorithm="sha256", value="deadbeef")
        assert checksum.algorithm == "sha256"
        assert checksum.value == "deadbeef"


# ---------------------------------------------------------------------------
# ImageFileInfo and TableFileInfo
# ---------------------------------------------------------------------------


class TestFileInfoModels:
    """Verify ImageFileInfo and TableFileInfo models."""

    def test_image_file_info(self) -> None:
        info: ImageFileInfo = ImageFileInfo(
            id="IMG_1",
            file_path="images/IMG_1.jpg",
            original_name="photo.jpg",
            size_bytes=2048,
            format="jpeg",
            width=1920,
            height=1080,
        )
        assert info.id == "IMG_1"
        assert info.width == 1920

    def test_table_file_info(self) -> None:
        info: TableFileInfo = TableFileInfo(
            id="TBL_1",
            file_path="tables/TBL_1.csv",
            original_name="data.csv",
            size_bytes=512,
            format="csv",
        )
        assert info.id == "TBL_1"
        assert info.format == "csv"

    def test_optional_fields(self) -> None:
        info: ImageFileInfo = ImageFileInfo(id="IMG_2", file_path="img.png")
        assert info.original_name is None
        assert info.size_bytes is None
        assert info.width is None


# ---------------------------------------------------------------------------
# BaseChunk model
# ---------------------------------------------------------------------------


class TestBaseChunkModel:
    """Verify BaseChunk model fields and defaults."""

    def test_from_dict(self) -> None:
        chunk: BaseChunk = BaseChunk(
            chunk_id="chunk_1",
            type="text",
            content="Hello world",
            path="section/intro",
        )
        assert chunk.chunk_id == "chunk_1"
        assert chunk.type == "text"
        assert chunk.content == "Hello world"
        assert chunk.path == "section/intro"

    def test_defaults(self) -> None:
        chunk: BaseChunk = BaseChunk(chunk_id="chunk_2", type="text")
        assert chunk.content == ""
        assert chunk.path is None
        assert chunk.page_nums is None

    def test_page_nums_supported(self) -> None:
        chunk: BaseChunk = BaseChunk(
            chunk_id="chunk_3", type="text", page_nums=[1, 2]
        )
        assert chunk.page_nums == [1, 2]


# ---------------------------------------------------------------------------
# TextChunk model
# ---------------------------------------------------------------------------


class TestTextChunkModel:
    """Verify TextChunk model fields and defaults."""

    def test_from_dict(self) -> None:
        chunk: TextChunk = TextChunk(
            chunk_id="text_1",
            content="Some text content",
            path="doc/section1",
            length=17,
            page_nums=[1, 2],
            tokens=["Some", "text", "content"],
            keywords=["text", "content"],
            summary="A text chunk",
            connect_to=[{"target": "img_1", "relation": "embeds"}],
            relationships=[{"target": "text_2", "type": "follows"}],
        )
        assert chunk.chunk_id == "text_1"
        assert chunk.type == "text"
        assert chunk.content == "Some text content"
        assert chunk.length == 17
        assert chunk.page_nums == [1, 2]
        assert chunk.tokens == ["Some", "text", "content"]
        assert chunk.keywords == ["text", "content"]
        assert chunk.summary == "A text chunk"
        assert chunk.connect_to is not None
        assert len(chunk.connect_to) == 1
        assert chunk.relationships is not None
        assert len(chunk.relationships) == 1

    def test_defaults(self) -> None:
        chunk: TextChunk = TextChunk(chunk_id="text_2")
        assert chunk.type == "text"
        assert chunk.length == 0
        assert chunk.tokens is None
        assert chunk.keywords is None
        assert chunk.summary is None
        assert chunk.connect_to is None
        assert chunk.relationships is None

    def test_is_instance_of_base_chunk(self) -> None:
        chunk: TextChunk = TextChunk(chunk_id="text_3")
        assert isinstance(chunk, BaseChunk)

    def test_accepts_tokens_list(self) -> None:
        chunk: TextChunk = TextChunk(
            chunk_id="text_4",
            tokens=["attention", "transformer"],
        )
        assert chunk.tokens == ["attention", "transformer"]


# ---------------------------------------------------------------------------
# ImageChunk model
# ---------------------------------------------------------------------------


class TestImageChunkModel:
    """Verify ImageChunk model fields, defaults, and format property."""

    def test_from_dict(self) -> None:
        chunk: ImageChunk = ImageChunk(
            chunk_id="IMG_1",
            content="A photo of a cat",
            file_path="images/IMG_1.jpg",
            original_name="cat.jpg",
            summary="Cat photo",
            data=b"\xff\xd8\xff\xe0",
        )
        assert chunk.chunk_id == "IMG_1"
        assert chunk.type == "image"
        assert chunk.content == "A photo of a cat"
        assert chunk.file_path == "images/IMG_1.jpg"
        assert chunk.original_name == "cat.jpg"
        assert chunk.data == b"\xff\xd8\xff\xe0"

    def test_defaults(self) -> None:
        chunk: ImageChunk = ImageChunk(chunk_id="IMG_2")
        assert chunk.type == "image"
        assert chunk.length == 0
        assert chunk.file_path is None
        assert chunk.original_name is None
        assert chunk.summary is None
        assert chunk.data == b""

    def test_format_property_from_file_path(self) -> None:
        chunk: ImageChunk = ImageChunk(
            chunk_id="IMG_3", file_path="images/IMG_3.png"
        )
        assert chunk.format == "png"

    def test_format_property_none_without_file_path(self) -> None:
        chunk: ImageChunk = ImageChunk(chunk_id="IMG_4")
        assert chunk.format is None

    def test_is_instance_of_base_chunk(self) -> None:
        chunk: ImageChunk = ImageChunk(chunk_id="IMG_5")
        assert isinstance(chunk, BaseChunk)

    def test_data_excluded_from_serialization(self) -> None:
        chunk: ImageChunk = ImageChunk(
            chunk_id="IMG_6", data=b"secret bytes"
        )
        dumped: Dict[str, Any] = chunk.model_dump()
        assert "data" not in dumped


# ---------------------------------------------------------------------------
# TableChunk model
# ---------------------------------------------------------------------------


class TestTableChunkModel:
    """Verify TableChunk model fields and defaults."""

    def test_from_dict(self) -> None:
        chunk: TableChunk = TableChunk(
            chunk_id="TBL_1",
            content="Revenue table",
            file_path="tables/TBL_1.html",
            original_name="revenue.html",
            table_type="financial",
            summary="Revenue data",
            html="<table><tr><td>100</td></tr></table>",
        )
        assert chunk.chunk_id == "TBL_1"
        assert chunk.type == "table"
        assert chunk.table_type == "financial"
        assert chunk.html == "<table><tr><td>100</td></tr></table>"

    def test_defaults(self) -> None:
        chunk: TableChunk = TableChunk(chunk_id="TBL_2")
        assert chunk.type == "table"
        assert chunk.length == 0
        assert chunk.file_path is None
        assert chunk.table_type is None
        assert chunk.html == ""

    def test_is_instance_of_base_chunk(self) -> None:
        chunk: TableChunk = TableChunk(chunk_id="TBL_3")
        assert isinstance(chunk, BaseChunk)

    def test_html_excluded_from_serialization(self) -> None:
        chunk: TableChunk = TableChunk(
            chunk_id="TBL_4", html="<table></table>"
        )
        dumped: Dict[str, Any] = chunk.model_dump()
        assert "html" not in dumped


# ---------------------------------------------------------------------------
# ParseResult
# ---------------------------------------------------------------------------


def _build_parse_result(
    chunks: Optional[List[Chunk]] = None,
) -> ParseResult:
    """Build a ParseResult with sensible defaults for testing."""
    manifest: Manifest = Manifest(
        version="1.0",
        job_id="job_test",
        source_file_name="test.pdf",
        statistics=Statistics(
            total_chunks=3,
            text_chunks=1,
            image_chunks=1,
            table_chunks=1,
            total_pages=2,
        ),
    )
    default_chunks: List[Chunk] = [
        TextChunk(
            chunk_id="text_1",
            content="Hello world",
            length=11,
        ),
        ImageChunk(
            chunk_id="img_1",
            content="A diagram",
            file_path="images/img_1.png",
            data=b"\x89PNG",
        ),
        TableChunk(
            chunk_id="tbl_1",
            content="Revenue table",
            html="<table><tr><td>100</td></tr></table>",
        ),
    ]
    return ParseResult(
        manifest=manifest,
        chunks=chunks if chunks is not None else default_chunks,
        chunks_slim=[
            SlimChunk(
                type="text",
                path="doc/section1",
                content="Hello world",
                summary="Greeting",
            )
        ],
        full_markdown="# Test\n\nHello world",
        hierarchy=None,
        toc_hierarchies=[{"toc_range": [1, 3]}],
        kb_csv="chunk_id,type\ntext_1,text\n",
        hierarchy_view_html="<html><body>Hierarchy</body></html>",
        raw_zip=b"fake zip bytes",
    )


class TestParseResult:
    """Verify ParseResult properties and lookup methods."""

    def test_text_chunks_filters_correctly(self) -> None:
        result: ParseResult = _build_parse_result()
        text_chunks: List[TextChunk] = result.text_chunks
        assert len(text_chunks) == 1
        assert text_chunks[0].chunk_id == "text_1"
        assert all(isinstance(c, TextChunk) for c in text_chunks)

    def test_image_chunks_filters_correctly(self) -> None:
        result: ParseResult = _build_parse_result()
        image_chunks: List[ImageChunk] = result.image_chunks
        assert len(image_chunks) == 1
        assert image_chunks[0].chunk_id == "img_1"
        assert all(isinstance(c, ImageChunk) for c in image_chunks)

    def test_table_chunks_filters_correctly(self) -> None:
        result: ParseResult = _build_parse_result()
        table_chunks: List[TableChunk] = result.table_chunks
        assert len(table_chunks) == 1
        assert table_chunks[0].chunk_id == "tbl_1"
        assert all(isinstance(c, TableChunk) for c in table_chunks)

    def test_all_chunks_accessible(self) -> None:
        result: ParseResult = _build_parse_result()
        assert len(result.chunks) == 3

    def test_get_chunk_finds_text_by_id(self) -> None:
        result: ParseResult = _build_parse_result()
        chunk: Optional[Chunk] = result.getChunk("text_1")
        assert chunk is not None
        assert chunk.chunk_id == "text_1"
        assert isinstance(chunk, TextChunk)

    def test_get_chunk_finds_image_by_id(self) -> None:
        result: ParseResult = _build_parse_result()
        chunk: Optional[Chunk] = result.getChunk("img_1")
        assert chunk is not None
        assert chunk.chunk_id == "img_1"
        assert isinstance(chunk, ImageChunk)

    def test_get_chunk_finds_table_by_id(self) -> None:
        result: ParseResult = _build_parse_result()
        chunk: Optional[Chunk] = result.getChunk("tbl_1")
        assert chunk is not None
        assert chunk.chunk_id == "tbl_1"
        assert isinstance(chunk, TableChunk)

    def test_get_chunk_returns_none_for_missing(self) -> None:
        result: ParseResult = _build_parse_result()
        assert result.getChunk("nonexistent") is None

    def test_empty_chunks_list(self) -> None:
        result: ParseResult = _build_parse_result(chunks=[])
        assert len(result.chunks) == 0
        assert len(result.text_chunks) == 0
        assert len(result.image_chunks) == 0
        assert len(result.table_chunks) == 0
        assert result.getChunk("anything") is None

    def test_full_markdown_accessible(self) -> None:
        result: ParseResult = _build_parse_result()
        assert result.full_markdown == "# Test\n\nHello world"

    def test_manifest_accessible(self) -> None:
        result: ParseResult = _build_parse_result()
        assert result.manifest is not None
        assert result.manifest.job_id == "job_test"

    def test_job_id_shortcut(self) -> None:
        result: ParseResult = _build_parse_result()
        assert result.job_id == "job_test"

    def test_statistics_shortcut(self) -> None:
        result: ParseResult = _build_parse_result()
        stats: Optional[Statistics] = result.statistics
        assert stats is not None
        assert stats.total_chunks == 3
        assert stats.text_chunks == 1

    def test_raw_zip_accessible(self) -> None:
        result: ParseResult = _build_parse_result()
        assert result.raw_zip == b"fake zip bytes"

    def test_optimized_result_fields_accessible(self) -> None:
        result: ParseResult = _build_parse_result()
        assert result.chunks_slim is not None
        assert result.chunks_slim[0].path == "doc/section1"
        assert result.toc_hierarchies == [{"toc_range": [1, 3]}]
        assert result.kb_csv == "chunk_id,type\ntext_1,text\n"
        assert result.hierarchy_view_html == "<html><body>Hierarchy</body></html>"
