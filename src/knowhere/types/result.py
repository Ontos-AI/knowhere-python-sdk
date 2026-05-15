"""Pydantic v2 models for parsed document results extracted from ZIP archives."""

from __future__ import annotations

import os
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from knowhere._exceptions import ValidationError


# ---------------------------------------------------------------------------
# Filename sanitisation helper
# ---------------------------------------------------------------------------

_UNSAFE_CHARS: re.Pattern[str] = re.compile(r'[\\/:?*"<>|]')


def _sanitizeFilename(name: str) -> str:
    """Return a cross-platform safe filename.

    * Replaces ``\\ / : ? * " < > |`` with ``_``
    * Strips leading/trailing whitespace and dots
    * Truncates to 200 characters
    """
    sanitized: str = _UNSAFE_CHARS.sub("_", name)
    sanitized = sanitized.strip().strip(".")
    return sanitized[:200]


def _ensurePathWithinDirectory(base: Path, target: Path) -> Path:
    """Raise ``ValidationError`` if *target* escapes *base* (Zip Slip prevention)."""
    resolved_base: Path = base.resolve()
    resolved_target: Path = target.resolve()
    if not str(resolved_target).startswith(str(resolved_base)):
        raise ValidationError(
            f"Path '{resolved_target}' escapes output directory '{resolved_base}'."
        )
    return resolved_target


# ---------------------------------------------------------------------------
# Manifest sub-models
# ---------------------------------------------------------------------------


class Statistics(BaseModel):
    """Aggregate statistics about the parsed document."""

    total_chunks: Optional[int] = 0
    text_chunks: Optional[int] = 0
    image_chunks: Optional[int] = 0
    table_chunks: Optional[int] = 0
    total_pages: Optional[int] = 0


class ImageFileInfo(BaseModel):
    """Metadata for an image file inside the result ZIP."""

    id: str
    file_path: str
    original_name: Optional[str] = None
    size_bytes: Optional[int] = None
    format: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class TableFileInfo(BaseModel):
    """Metadata for a table file inside the result ZIP."""

    id: str
    file_path: str
    original_name: Optional[str] = None
    size_bytes: Optional[int] = None
    format: Optional[str] = None


class Checksum(BaseModel):
    """Checksum information for integrity verification."""

    algorithm: str
    value: str


class FileIndex(BaseModel):
    """Index of files contained in the result ZIP."""

    chunks: Optional[str] = None
    markdown: Optional[str] = None
    chunks_slim: Optional[str] = None
    kb_csv: Optional[str] = None
    hierarchy: Optional[str] = None
    toc_hierarchies: Optional[str] = None
    hierarchy_view_html: Optional[str] = None
    images: List[ImageFileInfo] = Field(default_factory=list)
    tables: List[TableFileInfo] = Field(default_factory=list)


class ProcessingCost(BaseModel):
    """Billing details emitted by manifest v2."""

    micro_dollars: Optional[int] = None
    credits: Optional[float] = None


class ProcessingTiming(BaseModel):
    """Timing details emitted by manifest v2."""

    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None


class ProcessingMetadata(BaseModel):
    """Worker-side processing metadata emitted by manifest v2."""

    page_count: Optional[int] = None
    billing_status: Optional[str] = None
    cost: Optional[ProcessingCost] = None
    timing: Optional[ProcessingTiming] = None


class Manifest(BaseModel):
    """Top-level manifest describing the result ZIP contents."""

    version: Optional[str] = None
    job_id: Optional[str] = None
    data_id: Optional[str] = None
    source_file_name: Optional[str] = None
    processing_date: Optional[str] = None
    processing: Optional[ProcessingMetadata] = None
    checksum: Optional[Checksum] = None
    statistics: Optional[Statistics] = None
    files: Optional[FileIndex] = None
    hierarchy: Optional[Any] = Field(default=None, alias="HIERARCHY")


# ---------------------------------------------------------------------------
# DocNav models
# ---------------------------------------------------------------------------


class DocNavResourceItem(BaseModel):
    """A single image or table resource entry in ``doc_nav.json``."""

    path: str
    summary: Optional[str] = None


class DocNavResources(BaseModel):
    """Image and table resource summaries from ``doc_nav.json``."""

    images: List[DocNavResourceItem] = Field(default_factory=list)
    tables: List[DocNavResourceItem] = Field(default_factory=list)


class DocNavSection(BaseModel):
    """A document section entry in the ``doc_nav.json`` navigation tree."""

    title: str
    path: str
    level: int
    summary: Optional[str] = None
    chunk_count: int = 0
    children: List["DocNavSection"] = Field(default_factory=list)


class DocNav(BaseModel):
    """Top-level document navigation structure from ``doc_nav.json``."""

    sections: List[DocNavSection] = Field(default_factory=list)
    resources: Optional[DocNavResources] = None


# ---------------------------------------------------------------------------
# Chunk models
# ---------------------------------------------------------------------------


class ChunkMetadata(BaseModel):
    """Known worker metadata fields for a chunk.

    All fields are optional.  Unknown fields added by future worker
    versions are preserved thanks to ``model_config``.
    """

    model_config = {"extra": "allow"}

    length: Optional[int] = None
    page_nums: Optional[List[int]] = None
    tokens: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    summary: Optional[str] = None
    connect_to: Optional[List[Dict[str, Any]]] = None
    file_path: Optional[str] = None
    original_name: Optional[str] = None
    table_type: Optional[str] = None
    document_top_summary: Optional[str] = None


class BaseChunk(BaseModel):
    """Fields shared by every chunk type."""

    chunk_id: str
    type: str
    content: str = ""
    path: Optional[str] = None
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)


class TextChunk(BaseChunk):
    """A text chunk extracted from the document."""

    type: str = "text"


class ImageChunk(BaseChunk):
    """An image chunk — carries raw bytes loaded from the ZIP."""

    type: str = "image"
    file_path: Optional[str] = None
    data: bytes = Field(default=b"", exclude=True)

    model_config = {"arbitrary_types_allowed": True}

    @property
    def format(self) -> Optional[str]:
        """Infer image format from ``file_path`` extension."""
        if self.file_path:
            ext: str = os.path.splitext(self.file_path)[1].lstrip(".")
            return ext if ext else None
        return None

    def save(self, directory: Union[str, Path]) -> Path:
        """Write the image bytes to *directory*, returning the output path.

        The filename is derived from ``file_path``, sanitised for
        cross-platform safety.
        """
        dir_path: Path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        raw_name: str = os.path.basename(
            self.file_path or f"{self.chunk_id}.bin"
        )
        safe_name: str = _sanitizeFilename(raw_name)
        out_path: Path = _ensurePathWithinDirectory(
            dir_path, dir_path / safe_name
        )
        out_path.write_bytes(self.data)
        return out_path


class TableChunk(BaseChunk):
    """A table chunk — carries HTML loaded from the ZIP."""

    type: str = "table"
    file_path: Optional[str] = None
    html: str = Field(default="", exclude=True)

    def save(self, directory: Union[str, Path]) -> Path:
        """Write the table HTML to *directory*, returning the output path."""
        dir_path: Path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        raw_name: str = os.path.basename(
            self.file_path or f"{self.chunk_id}.html"
        )
        safe_name: str = _sanitizeFilename(raw_name)
        out_path: Path = _ensurePathWithinDirectory(
            dir_path, dir_path / safe_name
        )
        out_path.write_text(self.html, encoding="utf-8")
        return out_path


# Union of all chunk types
Chunk = Union[TextChunk, ImageChunk, TableChunk]


class SlimChunk(BaseModel):
    """Minimal chunk entry emitted in chunks_slim.json (legacy)."""

    type: str
    path: Optional[str] = None
    content: str = ""


# ---------------------------------------------------------------------------
# ParseResult — the top-level object returned to the user
# ---------------------------------------------------------------------------


class ParseResult:
    """Eagerly-loaded result of a document parsing job.

    Contains the manifest, all chunks (with image bytes and table HTML
    already loaded), the full markdown, the document navigation tree,
    and the raw ZIP bytes for archival purposes.

    Legacy fields (``chunks_slim``, ``hierarchy``, ``toc_hierarchies``,
    ``kb_csv``, ``hierarchy_view_html``) are kept for backward
    compatibility with older result ZIPs.  The current worker does not
    emit ``chunks_slim.json`` or ``hierarchy.json``.
    """

    manifest: Manifest
    chunks: List[Chunk]
    full_markdown: str
    raw_zip: bytes
    namespace: Optional[str]
    document_id: Optional[str]
    # Current worker output
    doc_nav: Optional[DocNav]
    # Legacy — the current worker no longer emits these files
    chunks_slim: Optional[List[SlimChunk]]
    hierarchy: Optional[Any]
    toc_hierarchies: Optional[Any]
    kb_csv: Optional[str]
    hierarchy_view_html: Optional[str]

    def __init__(
        self,
        *,
        manifest: Manifest,
        chunks: List[Chunk],
        full_markdown: str,
        raw_zip: bytes,
        doc_nav: Optional[DocNav] = None,
        namespace: Optional[str] = None,
        document_id: Optional[str] = None,
        # Legacy — the current worker no longer emits these files
        chunks_slim: Optional[List[SlimChunk]] = None,
        hierarchy: Optional[Any] = None,
        toc_hierarchies: Optional[Any] = None,
        kb_csv: Optional[str] = None,
        hierarchy_view_html: Optional[str] = None,
    ) -> None:
        self.manifest = manifest
        self.chunks = chunks
        self.full_markdown = full_markdown
        self.raw_zip = raw_zip
        self.doc_nav = doc_nav
        self.namespace = namespace
        self.document_id = document_id
        self.chunks_slim = chunks_slim
        self.hierarchy = hierarchy
        self.toc_hierarchies = toc_hierarchies
        self.kb_csv = kb_csv
        self.hierarchy_view_html = hierarchy_view_html

    # -- convenience properties --

    @property
    def text_chunks(self) -> List[TextChunk]:
        """Return only text chunks."""
        return [c for c in self.chunks if isinstance(c, TextChunk)]

    @property
    def image_chunks(self) -> List[ImageChunk]:
        """Return only image chunks."""
        return [c for c in self.chunks if isinstance(c, ImageChunk)]

    @property
    def table_chunks(self) -> List[TableChunk]:
        """Return only table chunks."""
        return [c for c in self.chunks if isinstance(c, TableChunk)]

    @property
    def job_id(self) -> Optional[str]:
        """Shortcut to ``manifest.job_id``."""
        return self.manifest.job_id

    @property
    def statistics(self) -> Optional[Statistics]:
        """Shortcut to ``manifest.statistics``."""
        return self.manifest.statistics

    # -- lookup --

    def getChunk(self, chunk_id: str) -> Optional[Chunk]:
        """Find a chunk by its ``chunk_id``, or return ``None``."""
        for chunk in self.chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
        return None

    # -- persistence --

    def save(self, directory: Union[str, Path]) -> Path:
        """Save the full result to *directory*.

        Creates the directory if needed and writes:
        * ``manifest.json`` — result manifest
        * ``chunks.json`` — all chunks
        * ``doc_nav.json`` — document navigation tree (if present)
        * ``full.md`` — the full markdown
        * ``images/`` — all image chunks
        * ``tables/`` — all table chunks
        * ``result.zip`` — the raw ZIP archive

        Legacy files (``chunks_slim.json``, ``hierarchy.json``, etc.) are
        also written when present for backward compatibility.

        Returns the resolved directory path.
        """
        dir_path: Path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        # Manifest / chunks
        manifest_path: Path = dir_path / "manifest.json"
        manifest_path.write_text(
            self.manifest.model_dump_json(indent=2, by_alias=True),
            encoding="utf-8",
        )

        chunks_path: Path = dir_path / "chunks.json"
        chunks_path.write_text(
            json.dumps([chunk.model_dump() for chunk in self.chunks], indent=2),
            encoding="utf-8",
        )

        if self.doc_nav is not None:
            doc_nav_path: Path = dir_path / "doc_nav.json"
            doc_nav_path.write_text(
                self.doc_nav.model_dump_json(indent=2),
                encoding="utf-8",
            )

        if self.chunks_slim is not None:
            chunks_slim_path: Path = dir_path / "chunks_slim.json"
            chunks_slim_path.write_text(
                json.dumps(
                    {"chunks": [chunk.model_dump() for chunk in self.chunks_slim]},
                    indent=2,
                ),
                encoding="utf-8",
            )

        # Full markdown
        md_path: Path = dir_path / "full.md"
        md_path.write_text(self.full_markdown, encoding="utf-8")

        if self.hierarchy is not None:
            hierarchy_path: Path = dir_path / "hierarchy.json"
            hierarchy_path.write_text(
                json.dumps(self.hierarchy, indent=2),
                encoding="utf-8",
            )

        if self.toc_hierarchies is not None:
            toc_hierarchies_path: Path = dir_path / "toc_hierarchies.json"
            toc_hierarchies_path.write_text(
                json.dumps(self.toc_hierarchies, indent=2),
                encoding="utf-8",
            )

        if self.kb_csv is not None:
            kb_csv_path: Path = dir_path / "kb.csv"
            kb_csv_path.write_text(self.kb_csv, encoding="utf-8")

        if self.hierarchy_view_html is not None:
            hierarchy_view_path: Path = dir_path / "hierarchy_view.html"
            hierarchy_view_path.write_text(
                self.hierarchy_view_html,
                encoding="utf-8",
            )

        # Images
        if self.image_chunks:
            images_dir: Path = dir_path / "images"
            images_dir.mkdir(exist_ok=True)
            for img in self.image_chunks:
                img.save(images_dir)

        # Tables
        if self.table_chunks:
            tables_dir: Path = dir_path / "tables"
            tables_dir.mkdir(exist_ok=True)
            for tbl in self.table_chunks:
                tbl.save(tables_dir)

        # Raw ZIP
        zip_path: Path = dir_path / "result.zip"
        zip_path.write_bytes(self.raw_zip)

        return dir_path.resolve()
