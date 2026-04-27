"""Pydantic models for canonical document lifecycle responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel


class Document(BaseModel):
    """Canonical document state returned by ``/v1/documents`` endpoints."""

    document_id: str
    namespace: str
    status: str
    current_job_result_id: Optional[str] = None
    source_file_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    """Response from ``GET /v1/documents``."""

    namespace: str
    documents: list[Document]


DocumentChunkType = Literal["text", "image", "table"]


class DocumentChunkPagination(BaseModel):
    """Pagination metadata returned by document chunk list endpoints."""

    page: int
    page_size: int
    total: int
    total_pages: int


class DocumentChunk(BaseModel):
    """One current-revision document chunk."""

    id: str
    chunk_id: str
    chunk_type: DocumentChunkType
    content: Optional[str] = None
    section_id: Optional[str] = None
    section_path: Optional[str] = None
    source_chunk_path: Optional[str] = None
    file_path: Optional[str] = None
    sort_order: int
    metadata: Dict[str, Any]
    asset_url: Optional[str] = None
    created_at: Optional[datetime] = None


class DocumentChunkListResponse(BaseModel):
    """Response from ``GET /v1/documents/{document_id}/chunks``."""

    document_id: str
    namespace: str
    job_result_id: Optional[str] = None
    job_id: Optional[str] = None
    chunks: list[DocumentChunk]
    pagination: DocumentChunkPagination


class DocumentChunkResponse(BaseModel):
    """Response from ``GET /v1/documents/{document_id}/chunks/{chunk_id}``."""

    document_id: str
    namespace: str
    job_result_id: Optional[str] = None
    job_id: Optional[str] = None
    chunk: DocumentChunk
