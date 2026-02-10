"""Parse a Knowhere result ZIP archive into a ``ParseResult``."""

from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from typing import Any, Dict, List, Optional

from knowhere._exceptions import ChecksumError, KnowhereError
from knowhere._logging import getLogger
from knowhere.types.result import (
    Chunk,
    ImageChunk,
    Manifest,
    ParseResult,
    TableChunk,
    TextChunk,
)

_logger = getLogger()


def _verifyChecksum(
    data: bytes,
    expected: str,
) -> None:
    """Raise ``ChecksumError`` if the SHA-256 of *data* does not match."""
    actual: str = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise ChecksumError(expected, actual)


def _safeZipPath(member_name: str, target_dir: str) -> str:
    """Validate that a ZIP member path does not escape *target_dir* (Zip Slip)."""
    abs_path: str = os.path.normpath(os.path.join(target_dir, member_name))
    if not abs_path.startswith(os.path.normpath(target_dir)):
        raise KnowhereError(
            f"Zip Slip detected: '{member_name}' escapes target directory."
        )
    return abs_path


def _readZipText(zf: zipfile.ZipFile, path: str) -> Optional[str]:
    """Read a text file from the ZIP, returning ``None`` if missing."""
    try:
        return zf.read(path).decode("utf-8")
    except KeyError:
        return None


def _readZipBytes(zf: zipfile.ZipFile, path: str) -> Optional[bytes]:
    """Read raw bytes from the ZIP, returning ``None`` if missing."""
    try:
        return zf.read(path)
    except KeyError:
        return None


def _extractFilePath(raw: Dict[str, Any]) -> Optional[str]:
    """Extract file_path from a chunk dict, checking multiple locations.

    The server may place ``file_path`` at the top level of the chunk or
    inside a nested ``metadata`` dict.  As a last resort the ``path``
    field is used, which typically stores the same value for image and
    table chunks produced by the current pipeline.
    """
    file_path: Optional[str] = raw.get("file_path")
    if file_path:
        return file_path
    metadata: Dict[str, Any] = raw.get("metadata", {})
    if isinstance(metadata, dict):
        meta_file_path: Optional[str] = metadata.get("file_path")
        if meta_file_path:
            return meta_file_path
    fallback: Optional[str] = raw.get("path")
    return fallback


def _buildChunks(
    raw_chunks: List[Dict[str, Any]],
    zf: zipfile.ZipFile,
) -> List[Chunk]:
    """Construct typed chunk objects, loading image bytes and table HTML."""
    chunks: List[Chunk] = []

    for raw in raw_chunks:
        chunk_type: str = raw.get("type", "text")

        if chunk_type == "image":
            image_data: bytes = b""
            # file_path may be at top level, inside metadata, or use path as fallback
            file_path: Optional[str] = _extractFilePath(raw)
            if file_path:
                image_data = _readZipBytes(zf, file_path) or b""
            metadata: Dict[str, Any] = raw.get("metadata", {})
            chunk: Chunk = ImageChunk(
                chunk_id=raw.get("chunk_id", ""),
                type="image",
                content=raw.get("content", ""),
                path=raw.get("path"),
                length=metadata.get("length", raw.get("length", 0)),
                file_path=file_path,
                original_name=metadata.get("original_name", raw.get("original_name")),
                summary=metadata.get("summary", raw.get("summary")),
                data=image_data,
            )
        elif chunk_type == "table":
            table_html: str = ""
            file_path = _extractFilePath(raw)
            if file_path:
                table_html = _readZipText(zf, file_path) or ""
            metadata = raw.get("metadata", {})
            chunk = TableChunk(
                chunk_id=raw.get("chunk_id", ""),
                type="table",
                content=raw.get("content", ""),
                path=raw.get("path"),
                length=metadata.get("length", raw.get("length", 0)),
                file_path=file_path,
                original_name=metadata.get("original_name", raw.get("original_name")),
                table_type=metadata.get("table_type", raw.get("table_type")),
                summary=metadata.get("summary", raw.get("summary")),
                html=table_html,
            )
        else:
            metadata = raw.get("metadata", {})
            chunk = TextChunk(
                chunk_id=raw.get("chunk_id", ""),
                type="text",
                content=raw.get("content", ""),
                path=raw.get("path"),
                length=metadata.get("length", raw.get("length", 0)),
                tokens=metadata.get("tokens", raw.get("tokens")),
                keywords=metadata.get("keywords", raw.get("keywords")),
                summary=metadata.get("summary", raw.get("summary")),
                relationships=metadata.get("relationships", raw.get("relationships")),
            )

        chunks.append(chunk)

    return chunks


def parseResultZip(
    zip_bytes: bytes,
    verify_checksum: bool = True,
    expected_checksum: Optional[str] = None,
) -> ParseResult:
    """Parse a Knowhere result ZIP archive into a ``ParseResult``.

    Args:
        zip_bytes: Raw bytes of the ZIP archive.
        verify_checksum: Whether to verify the SHA-256 checksum from the manifest.
        expected_checksum: Optional externally-provided checksum to verify against.

    Returns:
        A fully populated ``ParseResult`` with all chunks eagerly loaded.
    """
    zf: zipfile.ZipFile = zipfile.ZipFile(io.BytesIO(zip_bytes))

    # -- Manifest --
    manifest_text: Optional[str] = _readZipText(zf, "manifest.json")
    if manifest_text is None:
        raise KnowhereError("Result ZIP does not contain manifest.json.")
    manifest_data: Dict[str, Any] = json.loads(manifest_text)
    manifest: Manifest = Manifest.model_validate(manifest_data)

    # -- Checksum verification --
    if verify_checksum and manifest.checksum and manifest.checksum.value:
        _verifyChecksum(zip_bytes, manifest.checksum.value)
    if expected_checksum:
        _verifyChecksum(zip_bytes, expected_checksum)

    # -- Chunks --
    chunks_text: Optional[str] = _readZipText(zf, "chunks.json")
    parsed_chunks: Any = json.loads(chunks_text) if chunks_text else []
    # Handle both formats: raw list [...] or wrapped dict {"chunks": [...]}
    if isinstance(parsed_chunks, dict) and "chunks" in parsed_chunks:
        raw_chunks: List[Dict[str, Any]] = parsed_chunks["chunks"]
    elif isinstance(parsed_chunks, list):
        raw_chunks = parsed_chunks
    else:
        raw_chunks = []
    chunks: List[Chunk] = _buildChunks(raw_chunks, zf)

    # -- Full markdown --
    full_markdown: str = _readZipText(zf, "full.md") or ""

    # -- Hierarchy --
    hierarchy_text: Optional[str] = _readZipText(zf, "hierarchy.json")
    hierarchy: Optional[Any] = (
        json.loads(hierarchy_text) if hierarchy_text else None
    )

    zf.close()

    return ParseResult(
        manifest=manifest,
        chunks=chunks,
        full_markdown=full_markdown,
        hierarchy=hierarchy,
        raw_zip=zip_bytes,
    )
