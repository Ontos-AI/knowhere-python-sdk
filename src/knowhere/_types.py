"""Sentinel types, type aliases, and callback types for the Knowhere SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from knowhere.types.job import JobResult


class _NotGiven:
    """Sentinel singleton indicating a parameter was not provided by the caller.

    This is distinct from ``None``, which may be a valid value.  The global
    ``NOT_GIVEN`` instance should be used everywhere instead of constructing
    new instances.
    """

    _instance: Optional[_NotGiven] = None

    def __new__(cls) -> _NotGiven:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "NOT_GIVEN"

    def __bool__(self) -> bool:
        return False


NOT_GIVEN: _NotGiven = _NotGiven()
"""Singleton sentinel — use this instead of ``None`` for optional parameters."""

NotGiven: TypeAlias = _NotGiven

# ---------------------------------------------------------------------------
# Common type aliases
# ---------------------------------------------------------------------------

Headers: TypeAlias = dict[str, str]
Query: TypeAlias = dict[str, Any]

# ---------------------------------------------------------------------------
# Callback types
# ---------------------------------------------------------------------------

# Upload progress: (bytes_sent, total_bytes_or_none)
UploadProgressCallback: TypeAlias = Callable[[int, Union[int, None]], None]

# Poll progress: (current_job_result, elapsed_seconds)
# We use a string forward-ref to avoid a circular import with types.job
PollProgressCallback: TypeAlias = Callable[["JobResult", float], None]
