"""Pydantic models for retrieval query responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RetrievalCitation(BaseModel):
    """Source citation attached to a retrieval result."""

    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    source_file_name: Optional[str] = None
    section_path: Optional[str] = None


class RetrievalResult(BaseModel):
    """Canonical chunk result returned by ``POST /v1/retrieval/query``."""

    document_id: str
    chunk_id: str
    section_id: Optional[str] = None
    section_path: Optional[str] = None
    source_file_name: Optional[str] = None
    chunk_type: str
    content: str
    score: float
    asset_url: Optional[str] = None
    citation: Optional[RetrievalCitation] = None


class RetrievalQueryResponse(BaseModel):
    """Response from ``POST /v1/retrieval/query``."""

    namespace: str
    query: str
    results: list[RetrievalResult]
