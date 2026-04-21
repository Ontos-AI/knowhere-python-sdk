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
