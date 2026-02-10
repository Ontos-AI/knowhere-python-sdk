"""Pydantic v2 models for parsed document results extracted from ZIP archives."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


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
    """Raise ``ValueError`` if *target* escapes *base* (Zip Slip prevention)."""
    resolved_base: Path = base.resolve()
    resolved_target: Path = target.resolve()
    if not str(resolved_target).startswith(str(resolved_base)):
        raise ValueError(
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
    kb_csv: Optional[str] = None
    hierarchy: Optional[str] = None
    images: List[ImageFileInfo] = Field(default_factory=list)
    tables: List[TableFileInfo] = Field(default_factory=list)


class Manifest(BaseModel):
    """Top-level manifest describing the result ZIP contents."""

    version: Optional[str] = None
    job_id: Optional[str] = None
    data_id: Optional[str] = None
    source_file_name: Optional[str] = None
    processing_date: Optional[str] = None
    checksum: Optional[Checksum] = None
    statistics: Optional[Statistics] = None
    files: Optional[FileIndex] = None


# ---------------------------------------------------------------------------
# Chunk models
# ---------------------------------------------------------------------------


class BaseChunk(BaseModel):
    """Fields shared by every chunk type."""

    chunk_id: str
    type: str
    content: str = ""
    path: Optional[str] = None


class TextChunk(BaseChunk):
    """A text chunk extracted from the document."""

    type: str = "text"
    length: int = 0
    tokens: Optional[int] = None
    keywords: Optional[List[str]] = None
    summary: Optional[str] = None
    relationships: Optional[List[Union[Dict[str, Any], str]]] = None


class ImageChunk(BaseChunk):
    """An image chunk — carries raw bytes loaded from the ZIP."""

    type: str = "image"
    length: int = 0
    file_path: Optional[str] = None
    original_name: Optional[str] = None
    summary: Optional[str] = None
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

        The filename is derived from ``original_name`` or ``file_path``,
        sanitised for cross-platform safety.
        """
        dir_path: Path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        raw_name: str = self.original_name or os.path.basename(
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
    length: int = 0
    file_path: Optional[str] = None
    original_name: Optional[str] = None
    table_type: Optional[str] = None
    summary: Optional[str] = None
    html: str = Field(default="", exclude=True)

    def save(self, directory: Union[str, Path]) -> Path:
        """Write the table HTML to *directory*, returning the output path."""
        dir_path: Path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        raw_name: str = self.original_name or os.path.basename(
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


# ---------------------------------------------------------------------------
# ParseResult — the top-level object returned to the user
# ---------------------------------------------------------------------------


class ParseResult:
    """Eagerly-loaded result of a document parsing job.

    Contains the manifest, all chunks (with image bytes and table HTML
    already loaded), the full markdown, hierarchy data, and the raw ZIP
    bytes for archival purposes.
    """

    manifest: Manifest
    chunks: List[Chunk]
    full_markdown: str
    hierarchy: Optional[Any]
    raw_zip: bytes

    def __init__(
        self,
        *,
        manifest: Manifest,
        chunks: List[Chunk],
        full_markdown: str,
        hierarchy: Optional[Any],
        raw_zip: bytes,
    ) -> None:
        self.manifest = manifest
        self.chunks = chunks
        self.full_markdown = full_markdown
        self.hierarchy = hierarchy
        self.raw_zip = raw_zip

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
        * ``full.md`` — the full markdown
        * ``images/`` — all image chunks
        * ``tables/`` — all table chunks
        * ``result.zip`` — the raw ZIP archive

        Returns the resolved directory path.
        """
        dir_path: Path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        # Full markdown
        md_path: Path = dir_path / "full.md"
        md_path.write_text(self.full_markdown, encoding="utf-8")

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
