"""Base resource classes that hold a reference to the API client."""

from __future__ import annotations

from typing import Any, Dict, Optional, Type, TypeVar

from knowhere._base_client import AsyncAPIClient, SyncAPIClient

T = TypeVar("T")


class SyncAPIResource:
    """Base class for synchronous API resource namespaces."""

    _client: SyncAPIClient

    def __init__(self, client: SyncAPIClient) -> None:
        self._client = client

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        cast_to: Type[T],
        headers: Optional[Dict[str, str]] = None,
    ) -> T:
        """Delegate to the client's ``_request`` method."""
        return self._client._request(
            method,
            path,
            body=body,
            params=params,
            timeout=timeout,
            cast_to=cast_to,
            headers=headers,
        )


class AsyncAPIResource:
    """Base class for asynchronous API resource namespaces."""

    _client: AsyncAPIClient

    def __init__(self, client: AsyncAPIClient) -> None:
        self._client = client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        cast_to: Type[T],
        headers: Optional[Dict[str, str]] = None,
    ) -> T:
        """Delegate to the client's async ``_request`` method."""
        return await self._client._request(
            method,
            path,
            body=body,
            params=params,
            timeout=timeout,
            cast_to=cast_to,
            headers=headers,
        )
