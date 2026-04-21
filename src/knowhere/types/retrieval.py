"""Pydantic models for retrieval query responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RetrievalSource(BaseModel):
    """Caller-facing source reference attached to a retrieval result."""

    document_id: Optional[str] = None
    source_file_name: Optional[str] = None
    section_path: Optional[str] = None


class RetrievalResult(BaseModel):
    """Canonical chunk result returned by ``POST /v1/retrieval/query``."""

    chunk_type: str
    content: str
    score: float
    asset_url: Optional[str] = None
    source: RetrievalSource


class RetrievalQueryResponse(BaseModel):
    """Response from ``POST /v1/retrieval/query``."""

    namespace: str
    query: str
    results: list[RetrievalResult]
