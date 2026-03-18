"""Parse a Knowhere result ZIP archive into a ``ParseResult``."""

from __future__ import annotations

import ast
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
    TextChunkTokens,
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


def _normalizeTokenList(raw_tokens: List[Any]) -> List[str]:
    """Return a string-only token list with empty values removed."""
    normalized_tokens: List[str] = []
    for raw_token in raw_tokens:
        token_text: str = str(raw_token).strip()
        if token_text:
            normalized_tokens.append(token_text)
    return normalized_tokens


def _parseTokenString(raw_tokens: str) -> Optional[List[str]]:
    """Parse legacy string token formats into a token list when possible."""
    token_text: str = raw_tokens.strip()
    if not token_text:
        return None

    if token_text.startswith("[") and token_text.endswith("]"):
        try:
            literal_value: Any = ast.literal_eval(token_text)
        except (SyntaxError, ValueError):
            literal_value = None
        if isinstance(literal_value, list):
            return _normalizeTokenList(literal_value)
        if isinstance(literal_value, str):
            token_text = literal_value.strip()

    if ";" in token_text:
        return _normalizeTokenList(token_text.split(";"))
    if "->" in token_text:
        return _normalizeTokenList(token_text.split("->"))
    return None


def _parseTextChunkTokens(
    raw_tokens: Any,
    *,
    chunk_id: str,
) -> Optional[TextChunkTokens]:
    """Normalize text chunk tokens across old and new backend payloads."""
    if raw_tokens is None:
        return None
    if isinstance(raw_tokens, bool):
        raise KnowhereError(
            f"Invalid tokens payload for text chunk '{chunk_id}': expected int or token list, got bool."
        )
    if isinstance(raw_tokens, int):
        return raw_tokens
    if isinstance(raw_tokens, list):
        return _normalizeTokenList(raw_tokens)
    if isinstance(raw_tokens, str):
        stripped_tokens: str = raw_tokens.strip()
        if not stripped_tokens:
            return None
        if stripped_tokens.isdigit():
            return int(stripped_tokens)
        parsed_tokens: Optional[List[str]] = _parseTokenString(stripped_tokens)
        if parsed_tokens is not None:
            return parsed_tokens

    raise KnowhereError(
        "Invalid tokens payload for text chunk "
        f"'{chunk_id}': expected int, list[str], or delimited string, "
        f"got {type(raw_tokens).__name__}."
    )


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
            chunk_id: str = raw.get("chunk_id", "")
            raw_tokens: Any = metadata.get("tokens", raw.get("tokens"))
            chunk = TextChunk(
                chunk_id=chunk_id,
                type="text",
                content=raw.get("content", ""),
                path=raw.get("path"),
                length=metadata.get("length", raw.get("length", 0)),
                tokens=_parseTextChunkTokens(raw_tokens, chunk_id=chunk_id),
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
