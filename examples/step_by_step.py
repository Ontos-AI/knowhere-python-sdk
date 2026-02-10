"""Step-by-step job control using the low-level jobs.* methods.

Demonstrates granular control over the parsing pipeline:
  1. Create a job
  2. Upload a file with a progress callback
  3. Wait for completion with a progress callback
  4. Load and inspect the parse result

Prerequisites:
    export KNOWHERE_API_KEY="sk_..."
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from knowhere import Knowhere
from knowhere.types import Job, JobResult, ParseResult


def reportUploadProgress(bytes_sent: int, total_bytes: int) -> None:
    """Print upload progress to stdout."""
    percentage: float = (bytes_sent / total_bytes) * 100 if total_bytes else 0
    print(f"  Upload progress: {bytes_sent}/{total_bytes} bytes ({percentage:.1f}%)")


def reportJobProgress(job_result: JobResult, elapsed_seconds: float) -> None:
    """Print job polling progress to stdout."""
    print(f"  Job status: {job_result.status} (elapsed: {elapsed_seconds:.1f}s)")


def main() -> None:
    api_key: str | None = os.environ.get("KNOWHERE_API_KEY")
    if not api_key:
        print("Error: KNOWHERE_API_KEY environment variable is not set.")
        sys.exit(1)

    file_path: Path = Path("report.pdf")
    if not file_path.exists():
        print(f"Error: file not found at {file_path.resolve()}")
        sys.exit(1)

    client: Knowhere = Knowhere(api_key=api_key)

    # Step 1 -- Create a job -------------------------------------------------
    print("Step 1: Creating job...")
    job: Job = client.jobs.create(source_type="file")
    print(f"  Job created: {job.job_id}")

    # Step 2 -- Upload the file ----------------------------------------------
    print("\nStep 2: Uploading file...")
    client.jobs.upload(job, file=file_path, on_progress=reportUploadProgress)
    print("  Upload complete.")

    # Step 3 -- Wait for the job to finish -----------------------------------
    print("\nStep 3: Waiting for job to complete...")
    job_result: JobResult = client.jobs.wait(
        job.job_id,
        poll_interval=10.0,
        poll_timeout=1800.0,
        on_progress=reportJobProgress,
    )
    print(f"  Job finished with status: {job_result.status}")

    # Step 4 -- Load the parse result ----------------------------------------
    print("\nStep 4: Loading parse result...")
    result: ParseResult = client.jobs.load(job_result)
    print(f"  Total chunks: {result.statistics.total_chunks}")
    print(f"  Markdown length: {len(result.full_markdown)} characters")

    # Save results
    output_directory: Path = Path("output")
    result.save(output_directory)
    print(f"\nResults saved to: {output_directory.resolve()}")


if __name__ == "__main__":
    main()
