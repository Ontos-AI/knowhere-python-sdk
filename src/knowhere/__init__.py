"""Knowhere Python SDK — official client for the Knowhere document parsing API.

Quick start::

    from knowhere import Knowhere

    client = Knowhere(api_key="sk_...")
    result = client.parse(url="https://example.com/document.pdf")
    print(result.full_markdown)
"""

from __future__ import annotations

from knowhere._client import AsyncKnowhere, Knowhere
from knowhere._exceptions import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ChecksumError,
    ConflictError,
    GatewayTimeoutError,
    InternalServerError,
    InvalidStateError,
    JobFailedError,
    KnowhereError,
    NotFoundError,
    PaymentRequiredError,
    PermissionDeniedError,
    PollingTimeoutError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from knowhere._types import PollProgressCallback, UploadProgressCallback
from knowhere._version import __version__
from knowhere.types.document import Document, DocumentListResponse
from knowhere.types.job import Job, JobError, JobProgress, JobResult
from knowhere.types.params import ParsingParams, WebhookConfig
from knowhere.types.retrieval import (
    RetrievalChannel,
    RetrievalFilterMode,
    RetrievalSectionExclusion,
    RetrievalSource,
    RetrievalQueryResponse,
    RetrievalResult,
)
from knowhere.types.result import (
    BaseChunk,
    Checksum,
    Chunk,
    FileIndex,
    ImageChunk,
    ImageFileInfo,
    Manifest,
    ParseResult,
    ProcessingCost,
    ProcessingMetadata,
    ProcessingTiming,
    SlimChunk,
    Statistics,
    TableChunk,
    TableFileInfo,
    TextChunk,
)

__all__: list[str] = [
    # Clients
    "Knowhere",
    "AsyncKnowhere",
    # Version
    "__version__",
    # Exceptions
    "KnowhereError",
    "ValidationError",
    "InvalidStateError",
    "APIConnectionError",
    "APITimeoutError",
    "APIStatusError",
    "BadRequestError",
    "AuthenticationError",
    "PaymentRequiredError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "InternalServerError",
    "ServiceUnavailableError",
    "GatewayTimeoutError",
    "PollingTimeoutError",
    "JobFailedError",
    "ChecksumError",
    # Job types
    "Job",
    "JobError",
    "JobProgress",
    "JobResult",
    # Document types
    "Document",
    "DocumentListResponse",
    # Retrieval types
    "RetrievalChannel",
    "RetrievalFilterMode",
    "RetrievalSectionExclusion",
    "RetrievalSource",
    "RetrievalQueryResponse",
    "RetrievalResult",
    # Result types
    "ParseResult",
    "Manifest",
    "Statistics",
    "Checksum",
    "FileIndex",
    "ImageFileInfo",
    "TableFileInfo",
    "ProcessingCost",
    "ProcessingMetadata",
    "ProcessingTiming",
    "SlimChunk",
    "BaseChunk",
    "TextChunk",
    "ImageChunk",
    "TableChunk",
    "Chunk",
    # Param types
    "ParsingParams",
    "WebhookConfig",
    # Callback types
    "UploadProgressCallback",
    "PollProgressCallback",
]
