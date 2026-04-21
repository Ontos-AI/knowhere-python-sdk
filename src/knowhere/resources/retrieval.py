"""Retrieval resource for querying published documents."""

from __future__ import annotations

from typing import Any, Dict, Optional

from knowhere.resources._base import AsyncAPIResource, SyncAPIResource
from knowhere.types.retrieval import RetrievalQueryResponse


class Retrieval(SyncAPIResource):
    """Synchronous interface for ``/v1/retrieval`` endpoints."""

    def query(
        self,
        *,
        query: str,
        namespace: Optional[str] = None,
        top_k: Optional[int] = None,
        exclude_document_ids: Optional[list[str]] = None,
        exclude_sections: Optional[list[dict[str, str]]] = None,
    ) -> RetrievalQueryResponse:
        """Query published documents in a namespace."""
        body: Dict[str, Any] = {"query": query}
        if namespace is not None:
            body["namespace"] = namespace
        if top_k is not None:
            body["top_k"] = top_k
        if exclude_document_ids is not None:
            body["exclude_document_ids"] = exclude_document_ids
        if exclude_sections is not None:
            body["exclude_sections"] = exclude_sections

        return self._request(
            "POST",
            "v1/retrieval/query",
            body=body,
            cast_to=RetrievalQueryResponse,
        )


class AsyncRetrieval(AsyncAPIResource):
    """Asynchronous interface for ``/v1/retrieval`` endpoints."""

    async def query(
        self,
        *,
        query: str,
        namespace: Optional[str] = None,
        top_k: Optional[int] = None,
        exclude_document_ids: Optional[list[str]] = None,
        exclude_sections: Optional[list[dict[str, str]]] = None,
    ) -> RetrievalQueryResponse:
        """Query published documents in a namespace."""
        body: Dict[str, Any] = {"query": query}
        if namespace is not None:
            body["namespace"] = namespace
        if top_k is not None:
            body["top_k"] = top_k
        if exclude_document_ids is not None:
            body["exclude_document_ids"] = exclude_document_ids
        if exclude_sections is not None:
            body["exclude_sections"] = exclude_sections

        return await self._request(
            "POST",
            "v1/retrieval/query",
            body=body,
            cast_to=RetrievalQueryResponse,
        )
