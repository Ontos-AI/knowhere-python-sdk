"""Pydantic models for retrieval query responses."""

from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


RetrievalChannel = Literal["path", "content", "term"]
RetrievalFilterMode = Literal["delete", "keep"]


class RetrievalSectionExclusion(TypedDict):
    """Section exclusion for follow-up retrieval queries."""

    document_id: str
    section_path: str


class RetrievalSource(BaseModel):
    """Caller-facing source reference attached to a retrieval result."""

    document_id: Optional[str] = None
    source_file_name: Optional[str] = None
    section_path: Optional[str] = None


class RetrievalResult(BaseModel):
    """Canonical chunk result returned by ``POST /v1/retrieval/query``."""

    chunk_type: str
    content: str
    score: Optional[float] = None
    asset_url: Optional[str] = None
    source: RetrievalSource


class RetrievalReferencedChunk(BaseModel):
    """Cited evidence chunk returned by agentic retrieval."""

    chunk_id: str
    document_id: str
    chunk_type: str
    section_path: str
    file_path: Optional[str] = None
    job_id: Optional[str] = None
    asset_url: Optional[str] = None


class RetrievalQueryResponse(BaseModel):
    """Response from ``POST /v1/retrieval/query``.

    Three PRIMARY output fields for downstream agent consumption:

    - ``evidence_text``: hierarchical evidence tree for LLM context
    - ``decision_trace``: per-step navigation decisions (includes stop/failure)
    - ``referenced_chunks``: structured chunk citations for follow-up queries
    """

    namespace: str
    query: str
    router_used: str
    answer_text: Optional[str] = None
    referenced_chunks: list[RetrievalReferencedChunk] = Field(default_factory=list)
    evidence_text: Optional[str] = None
    stop_reason: Optional[str] = None
    failure_reason: Optional[str] = None
    results: list[RetrievalResult]
    decision_trace: Optional[list[dict[str, Any]]] = None
