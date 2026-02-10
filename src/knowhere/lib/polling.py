"""Polling helpers for waiting on job completion."""

from __future__ import annotations

import time
from typing import Optional

from knowhere._constants import (
    DEFAULT_POLL_INTERVAL,
    DEFAULT_POLL_TIMEOUT,
    MAX_POLL_INTERVAL,
    POLL_BACKOFF_MULTIPLIER,
    POLL_BACKOFF_THRESHOLD,
    TERMINAL_STATUSES,
)
from knowhere._exceptions import JobFailedError, PollingTimeoutError
from knowhere._logging import getLogger
from knowhere._types import PollProgressCallback
from knowhere.types.job import JobResult

_logger = getLogger()


def _calculateNextInterval(
    current_interval: float,
    elapsed: float,
) -> float:
    """Apply adaptive backoff after the threshold is reached."""
    if elapsed > POLL_BACKOFF_THRESHOLD:
        return min(current_interval * POLL_BACKOFF_MULTIPLIER, MAX_POLL_INTERVAL)
    return current_interval


def _handleTerminalState(job_result: JobResult) -> JobResult:
    """Return the result if done, raise ``JobFailedError`` if failed."""
    if job_result.is_done:
        return job_result
    if job_result.is_failed:
        error = job_result.error
        code: str = error.code if error else "unknown"
        message: str = error.message if error else "Job failed without error details."
        raise JobFailedError(job_result, code, message)
    return job_result


def syncPoll(
    client: object,
    job_id: str,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    poll_timeout: float = DEFAULT_POLL_TIMEOUT,
    on_progress: Optional[PollProgressCallback] = None,
) -> JobResult:
    """Poll ``GET /v1/jobs/{job_id}`` until a terminal status is reached.

    Uses adaptive backoff: after ``POLL_BACKOFF_THRESHOLD`` seconds the
    interval grows by ``POLL_BACKOFF_MULTIPLIER``, capped at
    ``MAX_POLL_INTERVAL``.
    """
    from knowhere._base_client import SyncAPIClient

    assert isinstance(client, SyncAPIClient)

    start: float = time.monotonic()
    current_interval: float = poll_interval

    while True:
        elapsed: float = time.monotonic() - start
        if elapsed >= poll_timeout:
            raise PollingTimeoutError(job_id, elapsed)

        job_result: JobResult = client._request(
            "GET",
            f"v1/jobs/{job_id}",
            cast_to=JobResult,
        )

        _logger.debug(
            "Poll job=%s status=%s progress=%s elapsed=%.1fs",
            job_id,
            job_result.status,
            job_result.progress,
            elapsed,
        )

        if on_progress:
            on_progress(job_result, elapsed)

        if job_result.status in TERMINAL_STATUSES:
            return _handleTerminalState(job_result)

        current_interval = _calculateNextInterval(current_interval, elapsed)
        remaining: float = poll_timeout - (time.monotonic() - start)
        sleep_time: float = min(current_interval, max(remaining, 0))
        if sleep_time <= 0:
            raise PollingTimeoutError(job_id, time.monotonic() - start)
        time.sleep(sleep_time)


async def asyncPoll(
    client: object,
    job_id: str,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    poll_timeout: float = DEFAULT_POLL_TIMEOUT,
    on_progress: Optional[PollProgressCallback] = None,
) -> JobResult:
    """Async version of :func:`syncPoll`."""
    import asyncio

    from knowhere._base_client import AsyncAPIClient

    assert isinstance(client, AsyncAPIClient)

    start: float = time.monotonic()
    current_interval: float = poll_interval

    while True:
        elapsed: float = time.monotonic() - start
        if elapsed >= poll_timeout:
            raise PollingTimeoutError(job_id, elapsed)

        job_result: JobResult = await client._request(
            "GET",
            f"v1/jobs/{job_id}",
            cast_to=JobResult,
        )

        _logger.debug(
            "Async poll job=%s status=%s progress=%s elapsed=%.1fs",
            job_id,
            job_result.status,
            job_result.progress,
            elapsed,
        )

        if on_progress:
            on_progress(job_result, elapsed)

        if job_result.status in TERMINAL_STATUSES:
            return _handleTerminalState(job_result)

        current_interval = _calculateNextInterval(current_interval, elapsed)
        remaining = poll_timeout - (time.monotonic() - start)
        sleep_time = min(current_interval, max(remaining, 0))
        if sleep_time <= 0:
            raise PollingTimeoutError(job_id, time.monotonic() - start)
        await asyncio.sleep(sleep_time)
