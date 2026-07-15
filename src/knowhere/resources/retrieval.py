"""Retrieval resource for querying published documents."""

from __future__ import annotations

from typing import Any, Dict, Optional

from knowhere.resources._base import AsyncAPIResource, SyncAPIResource
from knowhere.types.params import LLMConfig
from knowhere.types.retrieval import (
    RetrievalChunkType,
    RetrievalChannel,
    RetrievalFilterMode,
    RetrievalQueryResponse,
    RetrievalSectionExclusion,
)


class Retrieval(SyncAPIResource):
    """Synchronous interface for ``/v2/retrieval`` endpoints."""

    def query(
        self,
        *,
        query: str,
        namespace: Optional[str] = None,
        top_k: Optional[int] = None,
        use_agentic: Optional[bool] = None,
        data_type: Optional[int] = None,
        chunk_types: Optional[list[RetrievalChunkType]] = None,
        signal_paths: Optional[list[str]] = None,
        filter_mode: Optional[RetrievalFilterMode] = None,
        channels: Optional[list[RetrievalChannel]] = None,
        channel_weights: Optional[dict[RetrievalChannel, float]] = None,
        rerank: Optional[bool] = None,
        threshold: Optional[float] = None,
        internal_recall_k: Optional[int] = None,
        exclude_document_ids: Optional[list[str]] = None,
        exclude_sections: Optional[list[RetrievalSectionExclusion]] = None,
        llm_config: Optional[LLMConfig] = None,
    ) -> RetrievalQueryResponse:
        """Query published documents in a namespace."""
        body: Dict[str, Any] = {"query": query}
        if namespace is not None:
            body["namespace"] = namespace
        if top_k is not None:
            body["top_k"] = top_k
        if use_agentic is not None:
            body["use_agentic"] = use_agentic
        if data_type is not None:
            body["data_type"] = data_type
        if chunk_types is not None:
            body["chunk_types"] = chunk_types
        if signal_paths is not None:
            body["signal_paths"] = signal_paths
        if filter_mode is not None:
            body["filter_mode"] = filter_mode
        if channels is not None:
            body["channels"] = channels
        if channel_weights is not None:
            body["channel_weights"] = channel_weights
        if rerank is not None:
            body["rerank"] = rerank
        if threshold is not None:
            body["threshold"] = threshold
        if internal_recall_k is not None:
            body["internal_recall_k"] = internal_recall_k
        if exclude_document_ids is not None:
            body["exclude_document_ids"] = exclude_document_ids
        if exclude_sections is not None:
            body["exclude_sections"] = exclude_sections
        if llm_config is not None:
            body["llm_config"] = dict(llm_config)

        return self._request(
            "POST",
            self._versionedPath("retrieval/query"),
            body=body,
            cast_to=RetrievalQueryResponse,
        )


class AsyncRetrieval(AsyncAPIResource):
    """Asynchronous interface for ``/v2/retrieval`` endpoints."""

    async def query(
        self,
        *,
        query: str,
        namespace: Optional[str] = None,
        top_k: Optional[int] = None,
        use_agentic: Optional[bool] = None,
        data_type: Optional[int] = None,
        chunk_types: Optional[list[RetrievalChunkType]] = None,
        signal_paths: Optional[list[str]] = None,
        filter_mode: Optional[RetrievalFilterMode] = None,
        channels: Optional[list[RetrievalChannel]] = None,
        channel_weights: Optional[dict[RetrievalChannel, float]] = None,
        rerank: Optional[bool] = None,
        threshold: Optional[float] = None,
        internal_recall_k: Optional[int] = None,
        exclude_document_ids: Optional[list[str]] = None,
        exclude_sections: Optional[list[RetrievalSectionExclusion]] = None,
        llm_config: Optional[LLMConfig] = None,
    ) -> RetrievalQueryResponse:
        """Query published documents in a namespace."""
        body: Dict[str, Any] = {"query": query}
        if namespace is not None:
            body["namespace"] = namespace
        if top_k is not None:
            body["top_k"] = top_k
        if use_agentic is not None:
            body["use_agentic"] = use_agentic
        if data_type is not None:
            body["data_type"] = data_type
        if chunk_types is not None:
            body["chunk_types"] = chunk_types
        if signal_paths is not None:
            body["signal_paths"] = signal_paths
        if filter_mode is not None:
            body["filter_mode"] = filter_mode
        if channels is not None:
            body["channels"] = channels
        if channel_weights is not None:
            body["channel_weights"] = channel_weights
        if rerank is not None:
            body["rerank"] = rerank
        if threshold is not None:
            body["threshold"] = threshold
        if internal_recall_k is not None:
            body["internal_recall_k"] = internal_recall_k
        if exclude_document_ids is not None:
            body["exclude_document_ids"] = exclude_document_ids
        if exclude_sections is not None:
            body["exclude_sections"] = exclude_sections
        if llm_config is not None:
            body["llm_config"] = dict(llm_config)

        return await self._request(
            "POST",
            self._versionedPath("retrieval/query"),
            body=body,
            cast_to=RetrievalQueryResponse,
        )
