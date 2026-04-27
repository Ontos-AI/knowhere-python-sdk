"""Tests for the documents resource."""

from __future__ import annotations

from typing import Any, Dict

import httpx
import pytest
import respx

from tests.conftest import BASE_URL


DOCUMENTS_URL: str = f"{BASE_URL}/v1/documents"


def _make_document(status: str = "active") -> Dict[str, Any]:
    return {
        "document_id": "doc_123",
        "namespace": "support-center",
        "status": status,
        "current_job_result_id": "result_123",
        "source_file_name": "refund-policy.md",
        "created_at": "2026-04-21T08:00:00Z",
        "updated_at": "2026-04-21T08:30:00Z",
        "archived_at": "2026-04-21T09:00:00Z" if status == "archived" else None,
    }


def _make_document_chunk(chunk_type: str = "text") -> Dict[str, Any]:
    return {
        "id": "dchk_123",
        "chunk_id": "parser-chunk-1",
        "chunk_type": chunk_type,
        "content": "Chunk content",
        "section_id": "sec_123",
        "section_path": "Chapter 1",
        "source_chunk_path": "Chapter 1/Intro",
        "file_path": "images/figure-1.png" if chunk_type == "image" else None,
        "sort_order": 0,
        "metadata": {"summary": "Intro", "page_nums": [1]},
        "asset_url": "https://assets.example/figure-1.png" if chunk_type == "image" else None,
        "created_at": "2026-04-27T04:00:00Z",
    }


class TestDocumentsResource:
    """Verify document lifecycle calls."""

    @respx.mock
    def test_list_documents_sends_namespace_query(self, sync_client: Any) -> None:
        route = respx.get(DOCUMENTS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "namespace": "support-center",
                    "documents": [_make_document()],
                },
            )
        )

        response = sync_client.documents.list(namespace="support-center")

        assert route.called
        assert route.calls[0].request.url.params["namespace"] == "support-center"
        assert response.namespace == "support-center"
        assert response.documents[0].document_id == "doc_123"

    @respx.mock
    def test_list_documents_omits_namespace_when_defaulted(self, sync_client: Any) -> None:
        route = respx.get(DOCUMENTS_URL).mock(
            return_value=httpx.Response(
                200,
                json={"namespace": "default", "documents": []},
            )
        )

        response = sync_client.documents.list()

        assert route.called
        assert dict(route.calls[0].request.url.params) == {}
        assert response.namespace == "default"
        assert response.documents == []

    @respx.mock
    def test_get_document_returns_document_state(self, sync_client: Any) -> None:
        route = respx.get(f"{DOCUMENTS_URL}/doc_123").mock(
            return_value=httpx.Response(200, json=_make_document())
        )

        document = sync_client.documents.get("doc_123")

        assert route.called
        assert document.document_id == "doc_123"
        assert document.status == "active"

    @respx.mock
    def test_list_chunks_sends_optional_query_params(self, sync_client: Any) -> None:
        route = respx.get(f"{DOCUMENTS_URL}/doc_123/chunks").mock(
            return_value=httpx.Response(
                200,
                json={
                    "document_id": "doc_123",
                    "namespace": "support-center",
                    "job_result_id": "result_123",
                    "job_id": "job_123",
                    "chunks": [_make_document_chunk(chunk_type="table")],
                    "pagination": {
                        "page": 2,
                        "page_size": 10,
                        "total": 11,
                        "total_pages": 2,
                    },
                },
            )
        )

        response = sync_client.documents.list_chunks(
            "doc_123",
            page=2,
            page_size=10,
            chunk_type="table",
            include_asset_urls=True,
        )

        assert route.called
        assert route.calls[0].request.url.params["page"] == "2"
        assert route.calls[0].request.url.params["page_size"] == "10"
        assert route.calls[0].request.url.params["chunk_type"] == "table"
        assert route.calls[0].request.url.params["include_asset_urls"] == "true"
        assert response.document_id == "doc_123"
        assert response.chunks[0].id == "dchk_123"
        assert response.pagination.total_pages == 2

    @respx.mock
    def test_list_chunks_omits_default_query_params(self, sync_client: Any) -> None:
        route = respx.get(f"{DOCUMENTS_URL}/doc_123/chunks").mock(
            return_value=httpx.Response(
                200,
                json={
                    "document_id": "doc_123",
                    "namespace": "support-center",
                    "job_result_id": None,
                    "job_id": None,
                    "chunks": [],
                    "pagination": {
                        "page": 1,
                        "page_size": 50,
                        "total": 0,
                        "total_pages": 0,
                    },
                },
            )
        )

        response = sync_client.documents.list_chunks("doc_123")

        assert route.called
        assert dict(route.calls[0].request.url.params) == {}
        assert response.chunks == []
        assert response.pagination.total == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_chunk_requests_asset_urls_only_when_needed(
        self,
        async_client: Any,
    ) -> None:
        route = respx.get(f"{DOCUMENTS_URL}/doc_123/chunks/dchk_123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "document_id": "doc_123",
                    "namespace": "support-center",
                    "job_result_id": "result_123",
                    "job_id": "job_123",
                    "chunk": _make_document_chunk(chunk_type="image"),
                },
            )
        )

        response = await async_client.documents.get_chunk(
            "doc_123",
            "dchk_123",
            include_asset_urls=True,
        )

        assert route.called
        assert route.calls[0].request.url.params["include_asset_urls"] == "true"
        assert response.chunk.id == "dchk_123"
        assert response.chunk.asset_url == "https://assets.example/figure-1.png"

    @respx.mock
    def test_archive_document_returns_archived_state(self, sync_client: Any) -> None:
        route = respx.post(f"{DOCUMENTS_URL}/doc_123/archive").mock(
            return_value=httpx.Response(200, json=_make_document(status="archived"))
        )

        document = sync_client.documents.archive("doc_123")

        assert route.called
        assert document.document_id == "doc_123"
        assert document.status == "archived"
        assert document.archived_at is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_archive_document_returns_archived_state(
        self,
        async_client: Any,
    ) -> None:
        route = respx.post(f"{DOCUMENTS_URL}/doc_123/archive").mock(
            return_value=httpx.Response(200, json=_make_document(status="archived"))
        )

        document = await async_client.documents.archive("doc_123")

        assert route.called
        assert document.status == "archived"
