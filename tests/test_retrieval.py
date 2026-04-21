"""Tests for the retrieval resource."""

from __future__ import annotations

import json
from typing import Any, Dict

import httpx
import pytest
import respx

from tests.conftest import BASE_URL


RETRIEVAL_QUERY_URL: str = f"{BASE_URL}/v1/retrieval/query"


def _make_retrieval_response() -> Dict[str, Any]:
    return {
        "namespace": "support-center",
        "query": "refund policy",
        "results": [
            {
                "chunk_type": "text",
                "content": "Annual plans may be refunded within 30 days.",
                "score": 1.0,
                "source": {
                    "document_id": "doc_123",
                    "source_file_name": "refund-policy.md",
                    "section_path": "Policies / Billing / Refunds",
                },
            }
        ],
    }


class TestRetrievalQuery:
    """Verify retrieval.query() sends the public retrieval contract."""

    @respx.mock
    def test_query_sends_request_and_returns_results(self, sync_client: Any) -> None:
        route = respx.post(RETRIEVAL_QUERY_URL).mock(
            return_value=httpx.Response(200, json=_make_retrieval_response())
        )

        response = sync_client.retrieval.query(
            query="refund policy",
            namespace="support-center",
            top_k=5,
            exclude_document_ids=["doc_old"],
            exclude_sections=[
                {
                    "document_id": "doc_123",
                    "section_path": "Policies / Draft",
                }
            ],
        )

        assert route.called
        request_body: Dict[str, Any] = json.loads(route.calls[0].request.read())
        assert request_body == {
            "query": "refund policy",
            "namespace": "support-center",
            "top_k": 5,
            "exclude_document_ids": ["doc_old"],
            "exclude_sections": [
                {
                    "document_id": "doc_123",
                    "section_path": "Policies / Draft",
                }
            ],
        }
        assert response.namespace == "support-center"
        assert response.results[0].content == "Annual plans may be refunded within 30 days."
        assert response.results[0].source.document_id == "doc_123"
        assert response.results[0].source.source_file_name == "refund-policy.md"
        assert response.results[0].source.section_path == "Policies / Billing / Refunds"
        assert not hasattr(response.results[0], "citation")
        assert not hasattr(response.results[0], "chunk_id")
        assert not hasattr(response.results[0], "section_id")

    @respx.mock
    def test_query_omits_defaulted_optional_fields(self, sync_client: Any) -> None:
        route = respx.post(RETRIEVAL_QUERY_URL).mock(
            return_value=httpx.Response(200, json=_make_retrieval_response())
        )

        sync_client.retrieval.query(query="refund policy")

        request_body: Dict[str, Any] = json.loads(route.calls[0].request.read())
        assert request_body == {"query": "refund policy"}

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_query_sends_request_and_returns_results(
        self,
        async_client: Any,
    ) -> None:
        route = respx.post(RETRIEVAL_QUERY_URL).mock(
            return_value=httpx.Response(200, json=_make_retrieval_response())
        )

        response = await async_client.retrieval.query(
            query="refund policy",
            namespace="support-center",
            top_k=5,
        )

        assert route.called
        assert response.results[0].source.document_id == "doc_123"
