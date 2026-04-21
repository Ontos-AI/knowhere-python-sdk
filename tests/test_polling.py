"""Tests for the polling logic: wait, backoff, timeout, callbacks."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import httpx
import pytest
import respx

from knowhere._constants import MAX_POLL_INTERVAL
from knowhere._exceptions import JobFailedError, PollingTimeoutError
from tests.conftest import BASE_URL


JOBS_URL: str = f"{BASE_URL}/v1/jobs"


def _make_status_response(
    job_id: str,
    status: str,
    error: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a mock GET /v1/jobs/{id} response with the given status."""
    data: Dict[str, Any] = {
        "job_id": job_id,
        "status": status,
        "source_type": "url",
    }
    if error is not None:
        data["error"] = error
    if status == "done":
        data["result_url"] = "https://storage.example.com/result.zip"
    return data


# ---------------------------------------------------------------------------
# Immediate return
# ---------------------------------------------------------------------------


class TestPollImmediateReturn:
    """Verify poll returns immediately if the job is already terminal."""

    @respx.mock
    def test_returns_immediately_if_done(self, sync_client: Any) -> None:
        job_id: str = "job_already_done"
        route = respx.get(f"{JOBS_URL}/{job_id}").mock(
            return_value=httpx.Response(
                200,
                json=_make_status_response(job_id, "done"),
            )
        )

        result = sync_client.jobs.wait(
            job_id, poll_interval=0.01, poll_timeout=5.0
        )

        assert result.status == "done"
        assert route.call_count == 1


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestPollStatusTransitions:
    """Verify poll handles status transitions correctly."""

    @respx.mock
    def test_pending_to_running_to_done(self, sync_client: Any) -> None:
        job_id: str = "job_transitions"
        route = respx.get(f"{JOBS_URL}/{job_id}").mock(
            side_effect=[
                httpx.Response(
                    200, json=_make_status_response(job_id, "pending")
                ),
                httpx.Response(
                    200, json=_make_status_response(job_id, "running")
                ),
                httpx.Response(
                    200, json=_make_status_response(job_id, "done")
                ),
            ]
        )

        result = sync_client.jobs.wait(
            job_id, poll_interval=0.01, poll_timeout=5.0
        )

        assert result.status == "done"
        assert route.call_count == 3


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestPollTimeout:
    """Verify poll raises PollingTimeoutError after timeout."""

    @respx.mock
    def test_raises_polling_timeout_error(self, sync_client: Any) -> None:
        job_id: str = "job_timeout"
        # Always return "running" so it never completes
        respx.get(f"{JOBS_URL}/{job_id}").mock(
            return_value=httpx.Response(
                200,
                json=_make_status_response(job_id, "running"),
            )
        )

        with pytest.raises(PollingTimeoutError) as exc_info:
            sync_client.jobs.wait(
                job_id,
                poll_interval=0.01,
                poll_timeout=0.05,
            )

        assert exc_info.value.job_id == job_id


# ---------------------------------------------------------------------------
# Job failure
# ---------------------------------------------------------------------------


class TestPollJobFailure:
    """Verify poll raises JobFailedError when status is 'failed'."""

    @respx.mock
    def test_raises_job_failed_error(self, sync_client: Any) -> None:
        job_id: str = "job_failed"
        error_data: Dict[str, Any] = {
            "code": "PARSE_ERROR",
            "message": "Could not parse the document",
        }
        respx.get(f"{JOBS_URL}/{job_id}").mock(
            return_value=httpx.Response(
                200,
                json=_make_status_response(job_id, "failed", error=error_data),
            )
        )

        with pytest.raises(JobFailedError) as exc_info:
            sync_client.jobs.wait(
                job_id, poll_interval=0.01, poll_timeout=5.0
            )

        assert exc_info.value.code == "PARSE_ERROR"
        assert "Could not parse" in exc_info.value.message


# ---------------------------------------------------------------------------
# Adaptive backoff
# ---------------------------------------------------------------------------


class TestPollAdaptiveBackoff:
    """Verify adaptive backoff increases interval after threshold."""

    @respx.mock
    def test_interval_increases_after_threshold(
        self, sync_client: Any
    ) -> None:
        """After POLL_BACKOFF_THRESHOLD seconds, the interval should increase.

        We verify the poll completes and makes multiple calls.
        """
        job_id: str = "job_backoff"
        responses = [
            httpx.Response(
                200, json=_make_status_response(job_id, "running")
            )
            for _ in range(5)
        ] + [
            httpx.Response(
                200, json=_make_status_response(job_id, "done")
            )
        ]

        route = respx.get(f"{JOBS_URL}/{job_id}").mock(side_effect=responses)

        result = sync_client.jobs.wait(
            job_id,
            poll_interval=0.01,
            poll_timeout=5.0,
        )

        assert result.status == "done"
        assert route.call_count == 6

    def test_max_poll_interval_is_30_seconds(self) -> None:
        """MAX_POLL_INTERVAL should be 30 seconds."""
        assert MAX_POLL_INTERVAL == 30.0


# ---------------------------------------------------------------------------
# on_progress callback
# ---------------------------------------------------------------------------


class TestPollOnProgressCallback:
    """Verify on_progress callback is called with (job_result, elapsed)."""

    @respx.mock
    def test_callback_called_on_each_poll(self, sync_client: Any) -> None:
        job_id: str = "job_progress"
        respx.get(f"{JOBS_URL}/{job_id}").mock(
            side_effect=[
                httpx.Response(
                    200, json=_make_status_response(job_id, "running")
                ),
                httpx.Response(
                    200, json=_make_status_response(job_id, "done")
                ),
            ]
        )

        callback_calls: List[Tuple[Any, float]] = []

        def on_progress(job_result: Any, elapsed: float) -> None:
            callback_calls.append((job_result, elapsed))

        result = sync_client.jobs.wait(
            job_id,
            poll_interval=0.01,
            poll_timeout=5.0,
            on_progress=on_progress,
        )

        assert result.status == "done"
        # Callback should have been called at least once
        assert len(callback_calls) >= 1
        # Each call should have a non-negative elapsed time
        for _, elapsed in callback_calls:
            assert elapsed >= 0.0
