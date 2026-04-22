"""Tests for the Jobs resource: create, get, upload, wait, load."""

from __future__ import annotations

from typing import Any, Dict

import httpx
import respx

from tests.conftest import BASE_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

JOBS_URL: str = f"{BASE_URL}/v1/jobs"


# ---------------------------------------------------------------------------
# jobs.create()
# ---------------------------------------------------------------------------


class TestJobsCreate:
    """Verify jobs.create() sends the correct POST request."""

    @respx.mock
    def test_create_with_url_source(
        self,
        sync_client: Any,
    ) -> None:
        """POST /v1/jobs with source_type=url sends correct payload."""
        response_body: Dict[str, Any] = {
            "job_id": "job_test123",
            "status": "pending",
            "source_type": "url",
            "namespace": "support-center",
        }

        route = respx.post(JOBS_URL).mock(
            return_value=httpx.Response(200, json=response_body)
        )

        job = sync_client.jobs.create(
            source_type="url",
            source_url="https://example.com/doc.pdf",
        )

        assert route.called
        assert job.job_id == "job_test123"
        assert job.source_type == "url"
        assert job.status == "pending"
        assert job.namespace == "support-center"
        assert not hasattr(job, "document_id")

    @respx.mock
    def test_create_with_file_source(
        self,
        sync_client: Any,
        mock_job_response: Dict[str, Any],
    ) -> None:
        """POST /v1/jobs with source_type=file returns upload_url."""
        route = respx.post(JOBS_URL).mock(
            return_value=httpx.Response(200, json=mock_job_response)
        )

        job = sync_client.jobs.create(
            source_type="file",
            file_name="test.pdf",
        )

        assert route.called
        assert job.source_type == "file"
        assert job.upload_url is not None
        assert job.status == "waiting-file"

    @respx.mock
    def test_create_sends_correct_body(
        self,
        sync_client: Any,
    ) -> None:
        """Verify the POST body contains the expected fields."""
        response_body: Dict[str, Any] = {
            "job_id": "job_body_check",
            "status": "pending",
            "source_type": "url",
            "namespace": "support-center",
        }

        route = respx.post(JOBS_URL).mock(
            return_value=httpx.Response(200, json=response_body)
        )

        sync_client.jobs.create(
            source_type="url",
            source_url="https://example.com/doc.pdf",
            data_id="my_data_id",
            namespace="support-center",
            document_id="doc_123",
        )

        assert route.called
        request_body: Dict[str, Any] = route.calls[0].request.read()
        import json
        body: Dict[str, Any] = json.loads(request_body)
        assert body["source_type"] == "url"
        assert body["source_url"] == "https://example.com/doc.pdf"
        assert body["data_id"] == "my_data_id"
        assert body["namespace"] == "support-center"
        assert body["document_id"] == "doc_123"


# ---------------------------------------------------------------------------
# jobs.get()
# ---------------------------------------------------------------------------


class TestJobsGet:
    """Verify jobs.get() sends the correct GET request."""

    @respx.mock
    def test_get_returns_job_result(
        self,
        sync_client: Any,
        mock_job_result_response: Dict[str, Any],
    ) -> None:
        """GET /v1/jobs/{job_id} returns a JobResult."""
        job_id: str = "job_test123"
        route = respx.get(f"{JOBS_URL}/{job_id}").mock(
            return_value=httpx.Response(200, json=mock_job_result_response)
        )

        result = sync_client.jobs.get(job_id)

        assert route.called
        assert result.job_id == job_id
        assert result.status == "done"
        assert result.is_done is True


# ---------------------------------------------------------------------------
# jobs.upload()
# ---------------------------------------------------------------------------


class TestJobsUpload:
    """Verify jobs.upload() sends PUT to the presigned URL."""

    @respx.mock
    def test_upload_sends_put_with_job_object(
        self, sync_client: Any
    ) -> None:
        """Upload sends PUT with file content using a Job object."""
        from knowhere.types.job import Job

        upload_url: str = "https://storage.example.com/upload?token=abc"
        route = respx.put(upload_url).mock(
            return_value=httpx.Response(200)
        )

        job: Job = Job(
            job_id="job_upload",
            status="waiting-file",
            source_type="file",
            upload_url=upload_url,
            upload_headers={"Content-Type": "application/pdf"},
        )

        sync_client.jobs.upload(job, b"fake pdf content")

        assert route.called

    @respx.mock
    def test_upload_sends_put_with_url_string(
        self, sync_client: Any
    ) -> None:
        """Upload sends PUT when given a URL string directly."""
        upload_url: str = "https://storage.example.com/upload?token=def"
        route = respx.put(upload_url).mock(
            return_value=httpx.Response(200)
        )

        sync_client.jobs.upload(upload_url, b"fake pdf content")

        assert route.called


# ---------------------------------------------------------------------------
# jobs.wait()
# ---------------------------------------------------------------------------


class TestJobsWait:
    """Verify jobs.wait() polls until the job reaches a terminal status."""

    @respx.mock
    def test_wait_polls_until_done(
        self,
        sync_client: Any,
    ) -> None:
        """wait() returns when the job status becomes 'done'."""
        job_id: str = "job_test123"
        pending_response: Dict[str, Any] = {
            "job_id": job_id,
            "status": "running",
            "source_type": "url",
        }
        done_response: Dict[str, Any] = {
            "job_id": job_id,
            "status": "done",
            "source_type": "url",
            "result_url": "https://storage.example.com/result.zip",
        }

        route = respx.get(f"{JOBS_URL}/{job_id}").mock(
            side_effect=[
                httpx.Response(200, json=pending_response),
                httpx.Response(200, json=done_response),
            ]
        )

        result = sync_client.jobs.wait(
            job_id, poll_interval=0.01, poll_timeout=5.0
        )

        assert result.status == "done"
        assert route.call_count == 2


# ---------------------------------------------------------------------------
# jobs.load()
# ---------------------------------------------------------------------------


class TestJobsLoad:
    """Verify jobs.load() downloads ZIP and returns ParseResult."""

    @respx.mock
    def test_load_downloads_and_parses(
        self,
        sync_client: Any,
        sample_zip_bytes: bytes,
    ) -> None:
        """load() downloads the ZIP from result_url and returns ParseResult."""
        result_url: str = "https://storage.example.com/result.zip"
        route = respx.get(result_url).mock(
            return_value=httpx.Response(
                200,
                content=sample_zip_bytes,
                headers={"Content-Type": "application/zip"},
            )
        )

        parse_result = sync_client.jobs.load(
            result_url, verify_checksum=False
        )

        assert route.called
        assert parse_result.manifest is not None
        assert parse_result.manifest.job_id == "job_test123"

    @respx.mock
    def test_load_with_job_result_object(
        self,
        sync_client: Any,
        sample_zip_bytes: bytes,
    ) -> None:
        """load() accepts a JobResult object with result_url."""
        from knowhere.types.job import JobResult

        result_url: str = "https://storage.example.com/result.zip"
        route = respx.get(result_url).mock(
            return_value=httpx.Response(
                200,
                content=sample_zip_bytes,
                headers={"Content-Type": "application/zip"},
            )
        )

        job_result: JobResult = JobResult(
            job_id="job_load",
            status="done",
            source_type="url",
            namespace="support-center",
            document_id="doc_123",
            result_url=result_url,
        )

        parse_result = sync_client.jobs.load(
            job_result, verify_checksum=False
        )

        assert route.called
        assert parse_result.manifest is not None
        assert parse_result.namespace == "support-center"
        assert parse_result.document_id == "doc_123"
