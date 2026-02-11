"""Tests for the Knowhere and AsyncKnowhere client classes."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import pytest

from knowhere._exceptions import ValidationError

from knowhere._constants import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_UPLOAD_TIMEOUT,
)


# ---------------------------------------------------------------------------
# Sync client: Knowhere
# ---------------------------------------------------------------------------


class TestKnowhereClient:
    """Verify the synchronous Knowhere client constructor and properties."""

    def test_constructor_with_explicit_params(self) -> None:
        from knowhere import Knowhere

        client: Knowhere = Knowhere(
            api_key="sk_test_explicit",
            base_url="https://custom.api.example.com",
        )
        assert client.api_key == "sk_test_explicit"
        assert client.base_url == "https://custom.api.example.com"
        client.close()

    def test_constructor_reads_api_key_from_env(self) -> None:
        from knowhere import Knowhere

        with patch.dict(os.environ, {"KNOWHERE_API_KEY": "sk_from_env"}):
            client: Knowhere = Knowhere()
            assert client.api_key == "sk_from_env"
            client.close()

    def test_constructor_reads_base_url_from_env(self) -> None:
        from knowhere import Knowhere

        with patch.dict(
            os.environ,
            {
                "KNOWHERE_API_KEY": "sk_test",
                "KNOWHERE_BASE_URL": "https://env.api.example.com",
            },
        ):
            client: Knowhere = Knowhere()
            assert client.base_url == "https://env.api.example.com"
            client.close()

    def test_missing_api_key_raises_value_error(self) -> None:
        from knowhere import Knowhere

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("KNOWHERE_API_KEY", None)
            with pytest.raises(ValidationError, match="(?i)api.key"):
                Knowhere()

    def test_default_timeout(self) -> None:
        from knowhere import Knowhere

        client: Knowhere = Knowhere(api_key="sk_test")
        assert client.timeout == DEFAULT_TIMEOUT
        client.close()

    def test_default_upload_timeout(self) -> None:
        from knowhere import Knowhere

        client: Knowhere = Knowhere(api_key="sk_test")
        assert client.upload_timeout == DEFAULT_UPLOAD_TIMEOUT
        client.close()

    def test_default_max_retries(self) -> None:
        from knowhere import Knowhere

        client: Knowhere = Knowhere(api_key="sk_test")
        assert client.max_retries == DEFAULT_MAX_RETRIES
        client.close()

    def test_default_base_url(self) -> None:
        from knowhere import Knowhere

        client: Knowhere = Knowhere(api_key="sk_test")
        assert client.base_url == DEFAULT_BASE_URL
        client.close()

    def test_context_manager_closes_client(self) -> None:
        from knowhere import Knowhere

        with Knowhere(api_key="sk_test") as client:
            assert client.api_key == "sk_test"
        # After exiting context, the underlying httpx client should be closed
        assert client._client.is_closed

    def test_jobs_property_returns_jobs_instance(self) -> None:
        from knowhere import Knowhere

        client: Knowhere = Knowhere(api_key="sk_test")
        jobs: Any = client.jobs
        assert hasattr(jobs, "create")
        assert hasattr(jobs, "get")
        assert hasattr(jobs, "upload")
        assert hasattr(jobs, "wait")
        assert hasattr(jobs, "load")
        client.close()

    def test_base_url_trailing_slash_stripped(self) -> None:
        from knowhere import Knowhere

        client: Knowhere = Knowhere(
            api_key="sk_test",
            base_url="https://api.example.com/",
        )
        assert not client.base_url.endswith("/")
        client.close()

    def test_custom_timeout(self) -> None:
        from knowhere import Knowhere

        client: Knowhere = Knowhere(api_key="sk_test", timeout=120.0)
        assert client.timeout == 120.0
        client.close()

    def test_custom_max_retries(self) -> None:
        from knowhere import Knowhere

        client: Knowhere = Knowhere(api_key="sk_test", max_retries=10)
        assert client.max_retries == 10
        client.close()


# ---------------------------------------------------------------------------
# Async client: AsyncKnowhere
# ---------------------------------------------------------------------------


class TestAsyncKnowhereClient:
    """Verify the asynchronous AsyncKnowhere client constructor."""

    def test_constructor_with_explicit_params(self) -> None:
        from knowhere import AsyncKnowhere

        client: AsyncKnowhere = AsyncKnowhere(
            api_key="sk_test_async",
            base_url="https://async.api.example.com",
        )
        assert client.api_key == "sk_test_async"
        assert client.base_url == "https://async.api.example.com"

    def test_constructor_reads_api_key_from_env(self) -> None:
        from knowhere import AsyncKnowhere

        with patch.dict(os.environ, {"KNOWHERE_API_KEY": "sk_async_env"}):
            client: AsyncKnowhere = AsyncKnowhere()
            assert client.api_key == "sk_async_env"

    def test_missing_api_key_raises_value_error(self) -> None:
        from knowhere import AsyncKnowhere

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("KNOWHERE_API_KEY", None)
            with pytest.raises(ValidationError, match="(?i)api.key"):
                AsyncKnowhere()

    def test_default_values(self) -> None:
        from knowhere import AsyncKnowhere

        client: AsyncKnowhere = AsyncKnowhere(api_key="sk_test")
        assert client.timeout == DEFAULT_TIMEOUT
        assert client.upload_timeout == DEFAULT_UPLOAD_TIMEOUT
        assert client.max_retries == DEFAULT_MAX_RETRIES
        assert client.base_url == DEFAULT_BASE_URL

    @pytest.mark.asyncio
    async def test_async_context_manager_closes_client(self) -> None:
        from knowhere import AsyncKnowhere

        async with AsyncKnowhere(api_key="sk_test") as client:
            assert client.api_key == "sk_test"
        assert client._client.is_closed

    def test_jobs_property_returns_async_jobs_instance(self) -> None:
        from knowhere import AsyncKnowhere

        client: AsyncKnowhere = AsyncKnowhere(api_key="sk_test")
        jobs: Any = client.jobs
        assert hasattr(jobs, "create")
        assert hasattr(jobs, "get")
        assert hasattr(jobs, "upload")
        assert hasattr(jobs, "wait")
        assert hasattr(jobs, "load")
