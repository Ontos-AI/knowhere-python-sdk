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
from knowhere._types import AuthTokenProvider, PollProgressCallback, UploadProgressCallback
from knowhere._version import __version__
from knowhere.lib.document_metadata import (
    PYTHON_SDK_DOCUMENT_METADATA_DEFAULTS,
    merge_document_metadata_defaults,
)
from knowhere.types.document import (
    Document,
    DocumentChunk,
    DocumentChunkListResponse,
    DocumentChunkPagination,
    DocumentChunkResponse,
    DocumentChunkType,
    DocumentListPagination,
    DocumentListResponse,
    DocumentPageCitationSource,
)
from knowhere.types.job import Job, JobError, JobProgress, JobResult
from knowhere.types.page_citation import (
    PAGE_CITATION_ASSETS_METADATA_KEY,
    PageCitationAsset,
    PageCitationAssetContentType,
    PageCitationAssetSource,
)
from knowhere.types.params import (
    DocumentMetadata,
    LLMConfig,
    LLMModelsConfig,
    LLMProviderConfig,
    ParsingParams,
    WebhookConfig,
)
from knowhere.types.result import (
    BaseChunk,
    Checksum,
    Chunk,
    FileIndex,
    ImageChunk,
    ImageFileInfo,
    Manifest,
    PageChunk,
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
from knowhere.types.retrieval import (
    RetrievalChannel,
    RetrievalChunkType,
    RetrievalFilterMode,
    RetrievalQueryResponse,
    RetrievalReferencedChunk,
    RetrievalResult,
    RetrievalSectionExclusion,
    RetrievalSource,
)

__all__: list[str] = [
    # Clients
    "Knowhere",
    "AsyncKnowhere",
    # Version
    "__version__",
    "PYTHON_SDK_DOCUMENT_METADATA_DEFAULTS",
    "merge_document_metadata_defaults",
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
    "DocumentChunk",
    "DocumentChunkListResponse",
    "DocumentChunkPagination",
    "DocumentChunkResponse",
    "DocumentChunkType",
    "DocumentListPagination",
    "DocumentListResponse",
    "DocumentPageCitationSource",
    "PageCitationAsset",
    "PageCitationAssetContentType",
    "PageCitationAssetSource",
    "PAGE_CITATION_ASSETS_METADATA_KEY",
    # Retrieval types
    "RetrievalChannel",
    "RetrievalChunkType",
    "RetrievalFilterMode",
    "RetrievalReferencedChunk",
    "RetrievalSectionExclusion",
    "RetrievalSource",
    "RetrievalQueryResponse",
    "RetrievalResult",
    # Result types
    "ParseResult",
    "Manifest",
    "PageChunk",
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
    "DocumentMetadata",
    "LLMConfig",
    "LLMModelsConfig",
    "LLMProviderConfig",
    "ParsingParams",
    "WebhookConfig",
    # Callback types
    "UploadProgressCallback",
    "PollProgressCallback",
    "AuthTokenProvider",
]
