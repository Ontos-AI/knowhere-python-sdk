"""Error handling patterns for the Knowhere SDK.

Demonstrates how to catch and handle the various exception types
raised by the SDK, from specific HTTP errors to polling failures.

Prerequisites:
    export KNOWHERE_API_KEY="sk_..."
"""

from __future__ import annotations

import os
import sys

from knowhere import Knowhere
from knowhere import (
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    JobFailedError,
    NotFoundError,
    PollingTimeoutError,
    RateLimitError,
)
from knowhere.types import ParseResult


def demonstrateHttpErrors(client: Knowhere) -> None:
    """Show how to handle HTTP-level errors returned by the API."""
    print("--- HTTP error handling ---\n")

    try:
        result: ParseResult = client.parse(url="https://example.com/doc.pdf")
        print(f"Success: {result.statistics.total_chunks} chunks")

    except BadRequestError as err:
        # 400 -- invalid parameters or unsupported file type
        print(f"Bad request (400): {err}")

    except AuthenticationError as err:
        # 401 -- missing or invalid API key
        print(f"Authentication failed (401): {err}")

    except NotFoundError as err:
        # 404 -- resource does not exist
        print(f"Not found (404): {err}")

    except RateLimitError as err:
        # 429 -- too many requests; back off and retry
        print(f"Rate limited (429): {err}")
        print("Consider adding a delay before retrying.")

    except APIStatusError as err:
        # Catch-all for any other HTTP status error (5xx, etc.)
        print(f"API error (status {err.status_code}): {err}")


def demonstratePollingErrors(client: Knowhere) -> None:
    """Show how to handle errors during job polling."""
    print("\n--- Polling error handling ---\n")

    try:
        # Use a very short timeout to trigger PollingTimeoutError
        result: ParseResult = client.parse(url="https://example.com/large.pdf")
        print(f"Success: {result.statistics.total_chunks} chunks")

    except PollingTimeoutError as err:
        # The job did not finish within the allowed time
        print(f"Polling timed out: {err}")
        print("You can resume polling with client.jobs.wait(job_id).")

    except JobFailedError as err:
        # The server reported that the job failed
        print(f"Job failed: {err}")


def demonstrateGracefulFallback(client: Knowhere) -> None:
    """Show a combined try/except with graceful degradation."""
    print("\n--- Graceful fallback ---\n")

    try:
        result: ParseResult = client.parse(url="https://example.com/doc.pdf")
        print(f"Parsed {result.statistics.total_chunks} chunks.")

    except (BadRequestError, NotFoundError) as err:
        print(f"Client error -- cannot parse this document: {err}")

    except RateLimitError:
        print("Rate limited -- will retry later.")

    except (PollingTimeoutError, JobFailedError) as err:
        print(f"Processing error -- job did not complete: {err}")

    except APIStatusError as err:
        print(f"Unexpected API error ({err.status_code}): {err}")


def main() -> None:
    api_key: str | None = os.environ.get("KNOWHERE_API_KEY")
    if not api_key:
        print("Error: KNOWHERE_API_KEY environment variable is not set.")
        sys.exit(1)

    client: Knowhere = Knowhere(api_key=api_key)

    demonstrateHttpErrors(client)
    demonstratePollingErrors(client)
    demonstrateGracefulFallback(client)


if __name__ == "__main__":
    main()
