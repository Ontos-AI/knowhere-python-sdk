"""Pydantic models for retrieval query responses."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, TypedDict, Union

from pydantic import BaseModel, Field


RetrievalChannel = Literal["path", "content", "term"]
RetrievalChunkType = Literal["text", "image", "table", "page"]
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


class RetrievalTextPart(BaseModel):
    type: Literal["text"]
    text: str


class RetrievalImagePart(BaseModel):
    type: Literal["image"]
    media_type: str
    data: str


RetrievalEvidencePart = Annotated[
    Union[RetrievalTextPart, RetrievalImagePart],
    Field(discriminator="type"),
]


class RetrievalResult(BaseModel):
    """Canonical chunk result returned by ``POST /v2/retrieval/query``."""

    chunk_id: Optional[str] = None
    chunk_type: str
    content_source: Optional[str] = None
    content: str
    score: Optional[float] = None
    asset_url: Optional[str] = None
    source_chunk_path: Optional[str] = None
    file_path: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    source: RetrievalSource


class RetrievalReferencedChunk(BaseModel):
    """Cited evidence chunk returned by agentic retrieval."""

    chunk_id: str
    document_id: str
    chunk_type: str
    content_source: Optional[str] = None
    section_path: str
    source_chunk_path: Optional[str] = None
    file_path: Optional[str] = None
    job_id: Optional[str] = None
    asset_url: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class RetrievalQueryResponse(BaseModel):
    """Response from ``POST /v2/retrieval/query``.

    Downstream agents consume:

    - ``evidence``: composed parts (text/HTML and inline images)
    - ``evidence_text``: text projection of those parts
    - ``results``: raw path chunks for debug
    - ``decision_trace``: per-step navigation decisions (includes stop/failure)
    - ``referenced_chunks``: structured chunk citations for follow-up queries
    """

    namespace: str
    query: str
    router_used: str
    evidence: list[RetrievalEvidencePart] = Field(default_factory=list)
    answer_text: Optional[str] = None
    referenced_chunks: list[RetrievalReferencedChunk] = Field(default_factory=list)
    evidence_text: Optional[str] = None
    stop_reason: Optional[str] = None
    failure_reason: Optional[str] = None
    results: list[RetrievalResult]
    decision_trace: Optional[list[dict[str, Any]]] = None
