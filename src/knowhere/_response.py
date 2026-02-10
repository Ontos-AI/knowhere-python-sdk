"""Thin wrapper around ``httpx.Response`` for typed model parsing."""

from __future__ import annotations

from typing import Generic, Type, TypeVar

import httpx

T = TypeVar("T")


class APIResponse(Generic[T]):
    """Wraps an ``httpx.Response`` and provides typed parsing.

    Attributes:
        status_code: The HTTP status code.
        headers: The response headers.
    """

    status_code: int
    headers: httpx.Headers
    _response: httpx.Response
    _model_class: Type[T]

    def __init__(
        self,
        response: httpx.Response,
        model_class: Type[T],
    ) -> None:
        self._response = response
        self._model_class = model_class
        self.status_code = response.status_code
        self.headers = response.headers

    def parse(self) -> T:
        """Deserialise the response body into *model_class*.

        For Pydantic ``BaseModel`` subclasses the JSON body is validated
        through ``model_validate``.  For plain ``dict`` or ``str`` the
        raw value is returned directly.
        """
        from pydantic import BaseModel

        data = self._response.json()

        if isinstance(self._model_class, type) and issubclass(
            self._model_class, BaseModel
        ):
            return self._model_class.model_validate(data)

        # Fallback: return the raw JSON-decoded value cast to T
        return data  # type: ignore[no-any-return]
