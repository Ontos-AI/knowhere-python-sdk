"""High-level client classes: ``Knowhere`` (sync) and ``AsyncKnowhere`` (async).

These are the primary entry points for the SDK.  They extend the base HTTP
clients with a ``jobs`` resource namespace and a convenience ``parse()``
method that orchestrates the full create-upload-wait-load workflow.
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import BinaryIO, Optional, Union, overload

from knowhere._base_client import AsyncAPIClient, SyncAPIClient
from knowhere._constants import DEFAULT_POLL_INTERVAL, DEFAULT_POLL_TIMEOUT
from knowhere._exceptions import ValidationError
from knowhere._logging import getLogger
from knowhere._types import (
    PollProgressCallback,
    UploadProgressCallback,
)
from knowhere.resources.jobs import AsyncJobs, Jobs
from knowhere.types.job import Job, JobResult
from knowhere.types.params import ParsingParams, WebhookConfig
from knowhere.types.result import ParseResult

_logger = getLogger()


class Knowhere(SyncAPIClient):
    """Synchronous Knowhere client.

    Usage::

        client = Knowhere(api_key="sk_...")
        result = client.parse(url="https://example.com/doc.pdf")
        print(result.full_markdown)
    """

    @cached_property
    def jobs(self) -> Jobs:
        """Access the jobs resource namespace."""
        return Jobs(self)

    # -- overloaded parse signatures --

    @overload
    def parse(
        self,
        *,
        url: str,
        data_id: Optional[str] = ...,
        parsing_params: Optional[ParsingParams] = ...,
        webhook: Optional[WebhookConfig] = ...,
        poll_interval: float = ...,
        poll_timeout: float = ...,
        verify_checksum: bool = ...,
        on_upload_progress: Optional[UploadProgressCallback] = ...,
        on_poll_progress: Optional[PollProgressCallback] = ...,
    ) -> ParseResult: ...

    @overload
    def parse(
        self,
        *,
        file: Union[Path, BinaryIO, bytes],
        file_name: Optional[str] = ...,
        data_id: Optional[str] = ...,
        parsing_params: Optional[ParsingParams] = ...,
        webhook: Optional[WebhookConfig] = ...,
        poll_interval: float = ...,
        poll_timeout: float = ...,
        verify_checksum: bool = ...,
        on_upload_progress: Optional[UploadProgressCallback] = ...,
        on_poll_progress: Optional[PollProgressCallback] = ...,
    ) -> ParseResult: ...

    def parse(
        self,
        *,
        url: Optional[str] = None,
        file: Optional[Union[Path, BinaryIO, bytes]] = None,
        file_name: Optional[str] = None,
        data_id: Optional[str] = None,
        parsing_params: Optional[ParsingParams] = None,
        webhook: Optional[WebhookConfig] = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        poll_timeout: float = DEFAULT_POLL_TIMEOUT,
        verify_checksum: bool = True,
        on_upload_progress: Optional[UploadProgressCallback] = None,
        on_poll_progress: Optional[PollProgressCallback] = None,
    ) -> ParseResult:
        """Parse a document end-to-end: create job, upload, wait, load.

        Provide exactly one of *url* or *file*.
        """
        if url and file:
            raise ValidationError("Provide either 'url' or 'file', not both.")
        if not url and file is None:
            raise ValidationError("Provide either 'url' or 'file'.")

        # Determine source type and create job
        if url:
            job: Job = self.jobs.create(
                source_type="url",
                source_url=url,
                data_id=data_id,
                parsing_params=parsing_params,
                webhook=webhook,
            )
        else:
            resolved_name: Optional[str] = file_name
            if resolved_name is None and isinstance(file, Path):
                resolved_name = file.name
            job = self.jobs.create(
                source_type="file",
                file_name=resolved_name,
                data_id=data_id,
                parsing_params=parsing_params,
                webhook=webhook,
            )
            assert file is not None
            self.jobs.upload(job, file, on_progress=on_upload_progress)

        # Wait for completion
        job_result: JobResult = self.jobs.wait(
            job.job_id,
            poll_interval=poll_interval,
            poll_timeout=poll_timeout,
            on_progress=on_poll_progress,
        )

        # Load and return parsed result
        return self.jobs.load(job_result, verify_checksum=verify_checksum)


class AsyncKnowhere(AsyncAPIClient):
    """Asynchronous Knowhere client.

    Usage::

        async with AsyncKnowhere(api_key="sk_...") as client:
            result = await client.parse(url="https://example.com/doc.pdf")
            print(result.full_markdown)
    """

    @cached_property
    def jobs(self) -> AsyncJobs:
        """Access the async jobs resource namespace."""
        return AsyncJobs(self)

    @overload
    async def parse(
        self,
        *,
        url: str,
        data_id: Optional[str] = ...,
        parsing_params: Optional[ParsingParams] = ...,
        webhook: Optional[WebhookConfig] = ...,
        poll_interval: float = ...,
        poll_timeout: float = ...,
        verify_checksum: bool = ...,
        on_upload_progress: Optional[UploadProgressCallback] = ...,
        on_poll_progress: Optional[PollProgressCallback] = ...,
    ) -> ParseResult: ...

    @overload
    async def parse(
        self,
        *,
        file: Union[Path, BinaryIO, bytes],
        file_name: Optional[str] = ...,
        data_id: Optional[str] = ...,
        parsing_params: Optional[ParsingParams] = ...,
        webhook: Optional[WebhookConfig] = ...,
        poll_interval: float = ...,
        poll_timeout: float = ...,
        verify_checksum: bool = ...,
        on_upload_progress: Optional[UploadProgressCallback] = ...,
        on_poll_progress: Optional[PollProgressCallback] = ...,
    ) -> ParseResult: ...

    async def parse(
        self,
        *,
        url: Optional[str] = None,
        file: Optional[Union[Path, BinaryIO, bytes]] = None,
        file_name: Optional[str] = None,
        data_id: Optional[str] = None,
        parsing_params: Optional[ParsingParams] = None,
        webhook: Optional[WebhookConfig] = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        poll_timeout: float = DEFAULT_POLL_TIMEOUT,
        verify_checksum: bool = True,
        on_upload_progress: Optional[UploadProgressCallback] = None,
        on_poll_progress: Optional[PollProgressCallback] = None,
    ) -> ParseResult:
        """Parse a document end-to-end (async version)."""
        if url and file:
            raise ValidationError("Provide either 'url' or 'file', not both.")
        if not url and file is None:
            raise ValidationError("Provide either 'url' or 'file'.")

        if url:
            job: Job = await self.jobs.create(
                source_type="url",
                source_url=url,
                data_id=data_id,
                parsing_params=parsing_params,
                webhook=webhook,
            )
        else:
            resolved_name: Optional[str] = file_name
            if resolved_name is None and isinstance(file, Path):
                resolved_name = file.name
            job = await self.jobs.create(
                source_type="file",
                file_name=resolved_name,
                data_id=data_id,
                parsing_params=parsing_params,
                webhook=webhook,
            )
            assert file is not None
            await self.jobs.upload(job, file, on_progress=on_upload_progress)

        job_result: JobResult = await self.jobs.wait(
            job.job_id,
            poll_interval=poll_interval,
            poll_timeout=poll_timeout,
            on_progress=on_poll_progress,
        )

        return await self.jobs.load(
            job_result, verify_checksum=verify_checksum
        )