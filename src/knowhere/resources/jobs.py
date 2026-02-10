"""Jobs resource — create, get, upload, wait, and load job results."""

from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Union

import httpx

from knowhere._constants import DEFAULT_POLL_INTERVAL, DEFAULT_POLL_TIMEOUT
from knowhere._logging import getLogger
from knowhere._types import (
    PollProgressCallback,
    UploadProgressCallback,
)
from knowhere.lib.polling import asyncPoll, syncPoll
from knowhere.lib.result_parser import parseResultZip
from knowhere.lib.upload import asyncUploadFile, syncUploadFile
from knowhere.resources._base import AsyncAPIResource, SyncAPIResource
from knowhere.types.job import Job, JobResult
from knowhere.types.params import ParsingParams, WebhookConfig
from knowhere.types.result import ParseResult

_logger = getLogger()


class Jobs(SyncAPIResource):
    """Synchronous interface for the ``/v1/jobs`` endpoints."""

    def create(
        self,
        *,
        source_type: str,
        source_url: Optional[str] = None,
        file_name: Optional[str] = None,
        data_id: Optional[str] = None,
        parsing_params: Optional[ParsingParams] = None,
        webhook: Optional[WebhookConfig] = None,
    ) -> Job:
        """Create a new parsing job.

        Args:
            source_type: ``"url"`` or ``"file"``.
            source_url: URL to parse (required when ``source_type="url"``).
            file_name: Original filename (used when ``source_type="file"``).
            data_id: Optional idempotency / correlation identifier.
            parsing_params: Optional parsing configuration.
            webhook: Optional webhook configuration.

        Returns:
            A ``Job`` object with upload details if ``source_type="file"``.
        """
        body: Dict[str, Any] = {"source_type": source_type}
        if source_url is not None:
            body["source_url"] = source_url
        if file_name is not None:
            body["file_name"] = file_name
        if data_id is not None:
            body["data_id"] = data_id
        if parsing_params is not None:
            body["parsing_params"] = dict(parsing_params)
        if webhook is not None:
            body["webhook"] = dict(webhook)

        return self._request("POST", "v1/jobs", body=body, cast_to=Job)

    def get(self, job_id: str) -> JobResult:
        """Retrieve the current status and result of a job."""
        return self._request("GET", f"v1/jobs/{job_id}", cast_to=JobResult)

    def upload(
        self,
        job: Union[Job, str],
        file: Union[Path, BinaryIO, bytes],
        *,
        on_progress: Optional[UploadProgressCallback] = None,
    ) -> None:
        """Upload a file for a job that was created with ``source_type="file"``.

        Args:
            job: A ``Job`` object or a pre-signed upload URL string.
            file: The file to upload (path, binary stream, or raw bytes).
            on_progress: Optional callback ``(bytes_sent, total_bytes)``.
        """
        if isinstance(job, Job):
            if not job.upload_url:
                raise ValueError("Job does not have an upload URL.")
            upload_url: str = job.upload_url
            upload_headers: Optional[Dict[str, str]] = job.upload_headers
        else:
            upload_url = job
            upload_headers = None

        syncUploadFile(
            self._client._client,
            upload_url,
            upload_headers,
            file,
            on_progress,
            timeout=self._client.upload_timeout,
        )

    def wait(
        self,
        job_id: str,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        poll_timeout: float = DEFAULT_POLL_TIMEOUT,
        on_progress: Optional[PollProgressCallback] = None,
    ) -> JobResult:
        """Poll until the job reaches a terminal status."""
        return syncPoll(
            self._client,
            job_id,
            poll_interval=poll_interval,
            poll_timeout=poll_timeout,
            on_progress=on_progress,
        )

    def load(
        self,
        job_result: Union[JobResult, str],
        *,
        verify_checksum: bool = True,
    ) -> ParseResult:
        """Download and parse the result ZIP for a completed job.

        Args:
            job_result: A ``JobResult`` with ``result_url`` or a direct URL string.
            verify_checksum: Whether to verify the SHA-256 checksum.

        Returns:
            A fully populated ``ParseResult``.
        """
        if isinstance(job_result, JobResult):
            if not job_result.result_url:
                raise ValueError("JobResult does not have a result_url.")
            result_url: str = job_result.result_url
        else:
            result_url = job_result

        response: httpx.Response = self._client._client.get(
            result_url, timeout=self._client.upload_timeout
        )
        response.raise_for_status()
        zip_bytes: bytes = response.content

        return parseResultZip(zip_bytes, verify_checksum=verify_checksum)


class AsyncJobs(AsyncAPIResource):
    """Asynchronous interface for the ``/v1/jobs`` endpoints."""

    async def create(
        self,
        *,
        source_type: str,
        source_url: Optional[str] = None,
        file_name: Optional[str] = None,
        data_id: Optional[str] = None,
        parsing_params: Optional[ParsingParams] = None,
        webhook: Optional[WebhookConfig] = None,
    ) -> Job:
        """Create a new parsing job (async)."""
        body: Dict[str, Any] = {"source_type": source_type}
        if source_url is not None:
            body["source_url"] = source_url
        if file_name is not None:
            body["file_name"] = file_name
        if data_id is not None:
            body["data_id"] = data_id
        if parsing_params is not None:
            body["parsing_params"] = dict(parsing_params)
        if webhook is not None:
            body["webhook"] = dict(webhook)

        return await self._request("POST", "v1/jobs", body=body, cast_to=Job)

    async def get(self, job_id: str) -> JobResult:
        """Retrieve the current status and result of a job (async)."""
        return await self._request(
            "GET", f"v1/jobs/{job_id}", cast_to=JobResult
        )

    async def upload(
        self,
        job: Union[Job, str],
        file: Union[Path, BinaryIO, bytes],
        *,
        on_progress: Optional[UploadProgressCallback] = None,
    ) -> None:
        """Upload a file for a job (async)."""
        if isinstance(job, Job):
            if not job.upload_url:
                raise ValueError("Job does not have an upload URL.")
            upload_url: str = job.upload_url
            upload_headers: Optional[Dict[str, str]] = job.upload_headers
        else:
            upload_url = job
            upload_headers = None

        await asyncUploadFile(
            self._client._client,
            upload_url,
            upload_headers,
            file,
            on_progress,
            timeout=self._client.upload_timeout,
        )

    async def wait(
        self,
        job_id: str,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        poll_timeout: float = DEFAULT_POLL_TIMEOUT,
        on_progress: Optional[PollProgressCallback] = None,
    ) -> JobResult:
        """Poll until the job reaches a terminal status (async)."""
        return await asyncPoll(
            self._client,
            job_id,
            poll_interval=poll_interval,
            poll_timeout=poll_timeout,
            on_progress=on_progress,
        )

    async def load(
        self,
        job_result: Union[JobResult, str],
        *,
        verify_checksum: bool = True,
    ) -> ParseResult:
        """Download and parse the result ZIP (async)."""
        if isinstance(job_result, JobResult):
            if not job_result.result_url:
                raise ValueError("JobResult does not have a result_url.")
            result_url: str = job_result.result_url
        else:
            result_url = job_result

        response: httpx.Response = await self._client._client.get(
            result_url, timeout=self._client.upload_timeout
        )
        response.raise_for_status()
        zip_bytes: bytes = response.content

        return parseResultZip(zip_bytes, verify_checksum=verify_checksum)
