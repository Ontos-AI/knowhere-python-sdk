"""Pydantic models for canonical document lifecycle responses."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

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
