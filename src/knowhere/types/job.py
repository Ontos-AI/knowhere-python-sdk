"""Pydantic v2 models for job creation and job result responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel


class JobError(BaseModel):
    """Embedded error object returned when a job fails."""

    code: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Any] = None


class JobProgress(BaseModel):
    """Progress info returned by the server during parsing.

    The server may return progress as a dict with page-level detail.
    """

    total_pages: int = 0
    processed_pages: int = 0

    @property
    def fraction(self) -> float:
        """Return progress as a 0.0–1.0 fraction."""
        if self.total_pages <= 0:
            return 0.0
        return self.processed_pages / self.total_pages


class Job(BaseModel):
    """Response from ``POST /v1/jobs`` — represents a newly created job."""

    job_id: str
    status: str
    source_type: str
    namespace: Optional[str] = None
    document_id: Optional[str] = None
    data_id: Optional[str] = None
    created_at: Optional[datetime] = None
    upload_url: Optional[str] = None
    upload_headers: Optional[Dict[str, str]] = None
    expires_in: Optional[int] = None


class JobResult(BaseModel):
    """Response from ``GET /v1/jobs/{job_id}`` — full job status and result."""

    job_id: str
    status: str
    source_type: str
    namespace: Optional[str] = None
    document_id: Optional[str] = None
    data_id: Optional[str] = None
    created_at: Optional[datetime] = None
    progress: Optional[Union[float, JobProgress]] = None
    error: Optional[JobError] = None
    result: Optional[Dict[str, Any]] = None
    result_url: Optional[str] = None
    result_url_expires_at: Optional[datetime] = None
    file_name: Optional[str] = None
    file_extension: Optional[str] = None
    model: Optional[str] = None
    ocr_enabled: Optional[bool] = None
    duration_seconds: Optional[float] = None
    credits_spent: Optional[float] = None

    @property
    def is_terminal(self) -> bool:
        """Return ``True`` if the job has reached a terminal status."""
        return self.status in ("done", "failed")

    @property
    def is_done(self) -> bool:
        """Return ``True`` if the job completed successfully."""
        return self.status == "done"

    @property
    def is_failed(self) -> bool:
        """Return ``True`` if the job failed."""
        return self.status == "failed"
