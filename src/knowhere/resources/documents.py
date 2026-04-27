"""Documents resource for canonical document lifecycle operations."""

from __future__ import annotations

from typing import Any, Dict, Optional

from knowhere.resources._base import AsyncAPIResource, SyncAPIResource
from knowhere.types.document import (
    Document,
    DocumentChunkListResponse,
    DocumentChunkResponse,
    DocumentChunkType,
    DocumentListResponse,
)


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

    def list_chunks(
        self,
        document_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        chunk_type: Optional[DocumentChunkType] = None,
        include_asset_urls: bool = False,
    ) -> DocumentChunkListResponse:
        """List current-revision chunks for one canonical document."""
        params: Dict[str, Any] = _build_chunk_list_params(
            page=page,
            page_size=page_size,
            chunk_type=chunk_type,
            include_asset_urls=include_asset_urls,
        )

        return self._request(
            "GET",
            f"v1/documents/{document_id}/chunks",
            params=params or None,
            cast_to=DocumentChunkListResponse,
        )

    def get_chunk(
        self,
        document_id: str,
        document_chunk_id: str,
        *,
        include_asset_urls: bool = False,
    ) -> DocumentChunkResponse:
        """Get one current-revision chunk for one canonical document."""
        params: Dict[str, Any] = _build_chunk_get_params(
            include_asset_urls=include_asset_urls,
        )

        return self._request(
            "GET",
            f"v1/documents/{document_id}/chunks/{document_chunk_id}",
            params=params or None,
            cast_to=DocumentChunkResponse,
        )

    def archive(self, document_id: str) -> Document:
        """Archive one canonical document by ID."""
        return self._request(
            "POST",
            f"v1/documents/{document_id}/archive",
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

    async def list_chunks(
        self,
        document_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        chunk_type: Optional[DocumentChunkType] = None,
        include_asset_urls: bool = False,
    ) -> DocumentChunkListResponse:
        """List current-revision chunks for one canonical document."""
        params: Dict[str, Any] = _build_chunk_list_params(
            page=page,
            page_size=page_size,
            chunk_type=chunk_type,
            include_asset_urls=include_asset_urls,
        )

        return await self._request(
            "GET",
            f"v1/documents/{document_id}/chunks",
            params=params or None,
            cast_to=DocumentChunkListResponse,
        )

    async def get_chunk(
        self,
        document_id: str,
        document_chunk_id: str,
        *,
        include_asset_urls: bool = False,
    ) -> DocumentChunkResponse:
        """Get one current-revision chunk for one canonical document."""
        params: Dict[str, Any] = _build_chunk_get_params(
            include_asset_urls=include_asset_urls,
        )

        return await self._request(
            "GET",
            f"v1/documents/{document_id}/chunks/{document_chunk_id}",
            params=params or None,
            cast_to=DocumentChunkResponse,
        )

    async def archive(self, document_id: str) -> Document:
        """Archive one canonical document by ID."""
        return await self._request(
            "POST",
            f"v1/documents/{document_id}/archive",
            cast_to=Document,
        )


def _build_chunk_list_params(
    *,
    page: int,
    page_size: int,
    chunk_type: Optional[DocumentChunkType],
    include_asset_urls: bool,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if page != 1:
        params["page"] = page
    if page_size != 50:
        params["page_size"] = page_size
    if chunk_type is not None:
        params["chunk_type"] = chunk_type
    if include_asset_urls:
        params["include_asset_urls"] = True
    return params


def _build_chunk_get_params(*, include_asset_urls: bool) -> Dict[str, Any]:
    if not include_asset_urls:
        return {}
    return {"include_asset_urls": True}
