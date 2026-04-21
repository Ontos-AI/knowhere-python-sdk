"""Documents resource for canonical document lifecycle operations."""

from __future__ import annotations

from typing import Any, Dict, Optional

from knowhere.resources._base import AsyncAPIResource, SyncAPIResource
from knowhere.types.document import Document, DocumentListResponse


class Documents(SyncAPIResource):
    """Synchronous interface for ``/v1/documents`` endpoints."""

    def list(self, *, namespace: Optional[str] = None) -> DocumentListResponse:
        """List canonical documents in a namespace."""
        params: Dict[str, Any] = {}
        if namespace is not None:
            params["namespace"] = namespace

        return self._request(
            "GET",
            "v1/documents",
            params=params or None,
            cast_to=DocumentListResponse,
        )

    def get(self, document_id: str) -> Document:
        """Get one canonical document by ID."""
        return self._request(
            "GET",
            f"v1/documents/{document_id}",
            cast_to=Document,
        )

    def archive(self, document_id: str) -> Document:
        """Archive one canonical document by ID."""
        return self._request(
            "POST",
            f"v1/documents/{document_id}:archive",
            cast_to=Document,
        )


class AsyncDocuments(AsyncAPIResource):
    """Asynchronous interface for ``/v1/documents`` endpoints."""

    async def list(self, *, namespace: Optional[str] = None) -> DocumentListResponse:
        """List canonical documents in a namespace."""
        params: Dict[str, Any] = {}
        if namespace is not None:
            params["namespace"] = namespace

        return await self._request(
            "GET",
            "v1/documents",
            params=params or None,
            cast_to=DocumentListResponse,
        )

    async def get(self, document_id: str) -> Document:
        """Get one canonical document by ID."""
        return await self._request(
            "GET",
            f"v1/documents/{document_id}",
            cast_to=Document,
        )

    async def archive(self, document_id: str) -> Document:
        """Archive one canonical document by ID."""
        return await self._request(
            "POST",
            f"v1/documents/{document_id}:archive",
            cast_to=Document,
        )
