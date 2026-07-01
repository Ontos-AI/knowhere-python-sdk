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
from knowhere.types.params import ApiVersion


class Documents(SyncAPIResource):
    """Synchronous interface for ``/v1/documents`` endpoints."""

    def list(
        self,
        *,
        namespace: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        api_version: Optional[ApiVersion] = None,
    ) -> DocumentListResponse:
        """List canonical documents in a namespace."""
        params: Dict[str, Any] = _build_document_list_params(
            namespace=namespace,
            page=page,
            page_size=page_size,
        )

        return self._request(
            "GET",
            self._versionedPath("documents", api_version),
            params=params or None,
            cast_to=DocumentListResponse,
        )

    def get(
        self,
        document_id: str,
        *,
        api_version: Optional[ApiVersion] = None,
    ) -> Document:
        """Get one canonical document by ID."""
        return self._request(
            "GET",
            self._versionedPath(f"documents/{document_id}", api_version),
            cast_to=Document,
        )

    def list_chunks(
        self,
        document_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        chunk_type: Optional[DocumentChunkType] = None,
        include_asset_urls: Optional[bool] = None,
        api_version: Optional[ApiVersion] = None,
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
            self._versionedPath(f"documents/{document_id}/chunks", api_version),
            params=params or None,
            cast_to=DocumentChunkListResponse,
        )

    def get_chunk(
        self,
        document_id: str,
        document_chunk_id: str,
        *,
        include_asset_urls: Optional[bool] = None,
        api_version: Optional[ApiVersion] = None,
    ) -> DocumentChunkResponse:
        """Get one current-revision chunk for one canonical document."""
        params: Dict[str, Any] = _build_chunk_get_params(
            include_asset_urls=include_asset_urls,
        )

        return self._request(
            "GET",
            self._versionedPath(
                f"documents/{document_id}/chunks/{document_chunk_id}",
                api_version,
            ),
            params=params or None,
            cast_to=DocumentChunkResponse,
        )

    def archive(
        self,
        document_id: str,
        *,
        api_version: Optional[ApiVersion] = None,
    ) -> Document:
        """Archive one canonical document by ID."""
        return self._request(
            "POST",
            self._versionedPath(f"documents/{document_id}/archive", api_version),
            cast_to=Document,
        )


class AsyncDocuments(AsyncAPIResource):
    """Asynchronous interface for ``/v1/documents`` endpoints."""

    async def list(
        self,
        *,
        namespace: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        api_version: Optional[ApiVersion] = None,
    ) -> DocumentListResponse:
        """List canonical documents in a namespace."""
        params: Dict[str, Any] = _build_document_list_params(
            namespace=namespace,
            page=page,
            page_size=page_size,
        )

        return await self._request(
            "GET",
            self._versionedPath("documents", api_version),
            params=params or None,
            cast_to=DocumentListResponse,
        )

    async def get(
        self,
        document_id: str,
        *,
        api_version: Optional[ApiVersion] = None,
    ) -> Document:
        """Get one canonical document by ID."""
        return await self._request(
            "GET",
            self._versionedPath(f"documents/{document_id}", api_version),
            cast_to=Document,
        )

    async def list_chunks(
        self,
        document_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        chunk_type: Optional[DocumentChunkType] = None,
        include_asset_urls: Optional[bool] = None,
        api_version: Optional[ApiVersion] = None,
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
            self._versionedPath(f"documents/{document_id}/chunks", api_version),
            params=params or None,
            cast_to=DocumentChunkListResponse,
        )

    async def get_chunk(
        self,
        document_id: str,
        document_chunk_id: str,
        *,
        include_asset_urls: Optional[bool] = None,
        api_version: Optional[ApiVersion] = None,
    ) -> DocumentChunkResponse:
        """Get one current-revision chunk for one canonical document."""
        params: Dict[str, Any] = _build_chunk_get_params(
            include_asset_urls=include_asset_urls,
        )

        return await self._request(
            "GET",
            self._versionedPath(
                f"documents/{document_id}/chunks/{document_chunk_id}",
                api_version,
            ),
            params=params or None,
            cast_to=DocumentChunkResponse,
        )

    async def archive(
        self,
        document_id: str,
        *,
        api_version: Optional[ApiVersion] = None,
    ) -> Document:
        """Archive one canonical document by ID."""
        return await self._request(
            "POST",
            self._versionedPath(f"documents/{document_id}/archive", api_version),
            cast_to=Document,
        )


def _build_document_list_params(
    *,
    namespace: Optional[str],
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if namespace is not None:
        params["namespace"] = namespace
    if page != 1:
        params["page"] = page
    if page_size != 50:
        params["page_size"] = page_size
    return params


def _build_chunk_list_params(
    *,
    page: int,
    page_size: int,
    chunk_type: Optional[DocumentChunkType],
    include_asset_urls: Optional[bool],
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if page != 1:
        params["page"] = page
    if page_size != 50:
        params["page_size"] = page_size
    if chunk_type is not None:
        params["chunk_type"] = chunk_type
    if include_asset_urls is not None:
        params["include_asset_urls"] = include_asset_urls
    return params


def _build_chunk_get_params(*, include_asset_urls: Optional[bool]) -> Dict[str, Any]:
    if include_asset_urls is None:
        return {}
    return {"include_asset_urls": include_asset_urls}
