# Knowhere Python SDK — Usage Guide

Comprehensive reference for every feature, parameter, and pattern in the SDK.

## Table of Contents

- [Installation](#installation)
- [Authentication](#authentication)
- [Quick Start](#quick-start)
- [Parsing Documents](#parsing-documents)
- [Parsing Parameters](#parsing-parameters)
- [Working with Results](#working-with-results)
- [Chunk Types](#chunk-types)
- [Step-by-Step Control (Jobs API)](#step-by-step-control-jobs-api)
- [Retrieval and Document Lifecycle](#retrieval-and-document-lifecycle)
- [Async Usage](#async-usage)
- [Progress Callbacks](#progress-callbacks)
- [Error Handling](#error-handling)
- [Configuration](#configuration)
- [Retries](#retries)
- [Logging](#logging)
- [Supported File Formats](#supported-file-formats)
- [Webhooks](#webhooks)

---

## Installation

```sh
pip install knowhere-python-sdk
```

Or with [uv](https://docs.astral.sh/uv/):

```sh
uv add knowhere-python-sdk
```

## Authentication

The SDK requires an API key. You can provide it in three ways (highest priority first):

1. Constructor argument:

```python
import knowhere

client = knowhere.Knowhere(api_key="sk_...")
```

2. Environment variable:

```sh
export KNOWHERE_API_KEY="sk_..."
```

```python
client = knowhere.Knowhere()  # reads from env
```

3. `.env` file (via [python-dotenv](https://pypi.org/project/python-dotenv/)):

```
# .env
KNOWHERE_API_KEY=sk_...
```

```python
from dotenv import load_dotenv
load_dotenv()

client = knowhere.Knowhere()
```

## Quick Start

```python
import knowhere

client = knowhere.Knowhere(api_key="sk_...")

# Parse a document from URL
result = client.parse(url="https://example.com/report.pdf")

print(result.statistics.total_chunks)
print(result.full_markdown[:200])

for chunk in result.text_chunks:
    print(chunk.content[:80])
```

---

## Parsing Documents

The `parse()` method is the primary entry point. It orchestrates the full workflow: create a job, upload (if file), poll until done, and download + parse the result ZIP.

### Parse from URL

```python
result = client.parse(url="https://example.com/report.pdf")
```

### Parse from file

You can pass a `Path`, a binary file object, or raw `bytes`:

```python
from pathlib import Path

# Path object — file_name is inferred from the filename
result = client.parse(file=Path("report.pdf"))

# Explicit file_name (required for BinaryIO / bytes)
with open("report.pdf", "rb") as f:
    result = client.parse(file=f, file_name="report.pdf")

# Raw bytes
result = client.parse(file=pdf_bytes, file_name="report.pdf")
```

### All `parse()` parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | — | URL of the document to parse. Mutually exclusive with `file`. |
| `file` | `Path \| BinaryIO \| bytes` | — | Local file to parse. Mutually exclusive with `url`. |
| `file_name` | `str \| None` | `None` | Original filename. Auto-detected from `Path.name` if omitted. Required for `BinaryIO`/`bytes`. |
| `data_id` | `str \| None` | `None` | Your own correlation/idempotency identifier (max 128 chars). |
| `parsing_params` | `ParsingParams \| None` | `None` | Parsing configuration (see below). |
| `webhook` | `WebhookConfig \| None` | `None` | Webhook for completion notification. |
| `poll_interval` | `float` | `10.0` | Initial polling interval in seconds. |
| `poll_timeout` | `float` | `1800.0` | Maximum time to wait for completion (30 min). |
| `verify_checksum` | `bool` | `True` | Verify SHA-256 checksum of the downloaded ZIP. |
| `on_upload_progress` | callback | `None` | Called during file upload with `(bytes_sent, total_bytes)`. |
| `on_poll_progress` | callback | `None` | Called on each poll with `(job_result, elapsed_seconds)`. |

---

## Parsing Parameters

Pass a `ParsingParams` dict to control how the document is processed:

```python
result = client.parse(
    file=Path("report.pdf"),
    parsing_params={
        "model": "advanced",
        "ocr_enabled": True,
        "summary_image": True,
        "summary_table": True,
    },
)
```

### Full parameter reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `"base" \| "advanced"` | `"base"` | Parsing model. `"advanced"` uses a more capable model for complex layouts. |
| `ocr_enabled` | `bool` | `False` | Enable OCR for scanned documents and images. |
| `doc_type` | `"auto" \| "pdf" \| "docx" \| "txt" \| "md"` | `"auto"` | Document type hint. `"auto"` detects from file extension. |
| `smart_title_parse` | `bool` | `True` | Enable hierarchical title extraction from document structure. |
| `summary_image` | `bool` | `True` | Generate AI descriptions for images. This is the most credit-intensive option. |
| `summary_table` | `bool` | `True` | Generate AI summaries for tables. |
| `summary_txt` | `bool` | `True` | Generate AI summaries and keyword extraction for text chunks. |
| `add_frag_desc` | `str \| None` | `""` | Custom description to prepend to each fragment for context. |
| `kb_dir` | `str \| None` | `"Default_Root"` | Knowledge base directory for organizing results. |

### Cost optimization tips

If you don't need AI-generated summaries, disable them to reduce credit usage:

```python
result = client.parse(
    url="https://example.com/report.pdf",
    parsing_params={
        "summary_image": False,
        "summary_table": False,
        "summary_txt": False,
    },
)
```

---

## Working with Results

`client.parse()` returns a `ParseResult` object containing everything extracted from the document.

### ParseResult overview

```python
result = client.parse(url="https://example.com/report.pdf")

# Manifest — metadata about the parsing job
result.manifest.job_id            # "abc-123"
result.manifest.source_file_name  # "report.pdf"
result.manifest.processing_date   # "2025-01-15T10:30:00Z"

# Statistics — aggregate counts
result.statistics.total_chunks    # 152
result.statistics.text_chunks     # 120
result.statistics.image_chunks    # 22
result.statistics.table_chunks    # 10
result.statistics.total_pages     # 48

# Full markdown — the entire document as markdown
print(result.full_markdown)

# All chunks (mixed types)
print(len(result.chunks))         # 152

# Filtered by type
result.text_chunks                # List[TextChunk]
result.image_chunks               # List[ImageChunk]
result.table_chunks               # List[TableChunk]

# Lookup by ID
chunk = result.getChunk("chunk_42")

# Hierarchy data (document structure tree, if available)
result.hierarchy

# Raw ZIP bytes (for archival)
result.raw_zip
```

### Saving results to disk

```python
result = client.parse(file=Path("report.pdf"))

# Saves full.md, images/, tables/, and result.zip
result.save("./output/report/")
```

---

## Chunk Types

Every chunk shares a base set of fields (`chunk_id`, `type`, `content`, `path`). Each type adds its own fields.

### TextChunk

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `str` | Unique identifier |
| `type` | `str` | Always `"text"` |
| `content` | `str` | The text content |
| `path` | `str \| None` | Document structure path (e.g. `"Section 1 > Subsection 2"`) |
| `length` | `int` | Character count |
| `tokens` | `List[str] \| None` | Tokenized words returned by the parser pipeline |
| `keywords` | `List[str] \| None` | Extracted keywords (requires `summary_txt: True`) |
| `summary` | `str \| None` | AI-generated summary (requires `summary_txt: True`) |
| `relationships` | `List \| None` | Relationships to other chunks |

```python
for chunk in result.text_chunks:
    print(f"[{chunk.chunk_id}] {chunk.content[:60]}...")
    if chunk.keywords:
        print(f"  Keywords: {', '.join(chunk.keywords)}")
    if chunk.summary:
        print(f"  Summary: {chunk.summary}")
```

### ImageChunk

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `str` | Unique identifier |
| `type` | `str` | Always `"image"` |
| `content` | `str` | Text content associated with the image |
| `file_path` | `str \| None` | Path within the ZIP |
| `original_name` | `str \| None` | Original filename |
| `summary` | `str \| None` | AI-generated image description (requires `summary_image: True`) |
| `data` | `bytes` | Raw image bytes (loaded from ZIP) |
| `format` | `str \| None` | Image format inferred from extension (property) |

```python
for img in result.image_chunks:
    print(f"{img.file_path} ({len(img.data)} bytes, {img.format})")
    if img.summary:
        print(f"  Description: {img.summary}")
    img.save("./output/images/")  # writes to disk
```

### TableChunk

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `str` | Unique identifier |
| `type` | `str` | Always `"table"` |
| `content` | `str` | Text representation of the table |
| `file_path` | `str \| None` | Path within the ZIP |
| `original_name` | `str \| None` | Original filename |
| `table_type` | `str \| None` | Table classification |
| `summary` | `str \| None` | AI-generated table summary (requires `summary_table: True`) |
| `html` | `str` | Full HTML of the table (loaded from ZIP) |

```python
for tbl in result.table_chunks:
    print(f"{tbl.file_path}: {tbl.html[:100]}...")
    tbl.save("./output/tables/")  # writes HTML file to disk
```

---

## Step-by-Step Control (Jobs API)

For granular control over the parsing workflow, use the `jobs` resource directly instead of the convenience `parse()` method.

```python
from pathlib import Path

# Step 1: Create a parsing job
job = client.jobs.create(
    source_type="file",
    file_name="report.pdf",
    namespace="support-center",
    parsing_params={"model": "advanced", "ocr_enabled": True},
)
print(job.document_id)  # Persist this value for update/archive flows.

# Step 2: Upload file to the presigned URL
client.jobs.upload(job, file=Path("report.pdf"))

# Step 3: Poll until done (adaptive backoff)
job_result = client.jobs.wait(
    job.job_id,
    poll_interval=10.0,
    poll_timeout=1800.0,
)

# Step 4: Download and parse results
result = client.jobs.load(job_result)
print(result.statistics)
```

### `jobs.create()` parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_type` | `"url" \| "file"` | — | Required. Whether parsing from URL or uploaded file. |
| `source_url` | `str \| None` | `None` | URL to parse (required when `source_type="url"`). |
| `file_name` | `str \| None` | `None` | Original filename (used when `source_type="file"`). |
| `namespace` | `str \| None` | `None` | Retrieval namespace. The server defaults to `"default"` when omitted. |
| `document_id` | `str \| None` | `None` | Existing document ID when creating an update job. Omit for a new document. |
| `data_id` | `str \| None` | `None` | Your own correlation/idempotency identifier. |
| `parsing_params` | `ParsingParams \| None` | `None` | Parsing configuration. |
| `webhook` | `WebhookConfig \| None` | `None` | Webhook for completion notification. |

Returns a `Job` object:

```python
job.job_id          # "abc-123"
job.status          # "pending"
job.source_type     # "file"
job.namespace       # "support-center"
job.document_id     # "doc_..." — persist this for updates and archive calls
job.upload_url      # presigned URL (for file uploads)
job.upload_headers  # headers to include in the upload request
job.expires_in      # seconds until upload URL expires
```

### `jobs.upload()`

```python
# From a Job object
client.jobs.upload(job, file=Path("report.pdf"))

# With progress tracking
client.jobs.upload(
    job,
    file=Path("report.pdf"),
    on_progress=lambda sent, total: print(f"{sent}/{total} bytes"),
)

# From raw bytes
client.jobs.upload(job, file=pdf_bytes)
```

### `jobs.get()` — check status

```python
job_result = client.jobs.get("abc-123")
print(job_result.status)           # "processing", "done", "failed"
print(job_result.is_done)          # True/False
print(job_result.is_failed)        # True/False
print(job_result.duration_seconds) # 12.5
print(job_result.credits_spent)    # 3.0
```

### `jobs.wait()` — poll until done

```python
job_result = client.jobs.wait(
    "abc-123",
    poll_interval=10.0,   # initial interval (seconds)
    poll_timeout=1800.0,  # max wait time (seconds)
    on_progress=lambda jr, elapsed: print(f"{jr.status} ({elapsed:.0f}s)"),
)
```

The poller uses adaptive backoff: it starts at `poll_interval` and gradually increases up to 30s, with a faster ramp after 60s of elapsed time.

### `jobs.load()` — download results

```python
result = client.jobs.load(job_result)
# or pass a URL directly:
result = client.jobs.load("https://storage.example.com/result.zip")
```

---

## Retrieval and Document Lifecycle

The retrieval APIs operate on canonical documents that are published after a
job completes. For new documents, the server generates `document_id` during
`jobs.create()`. Store that ID in your application if you need to update or
archive the same document later.

### Create a retrievable document

```python
job = client.jobs.create(
    source_type="url",
    source_url="https://example.com/manual.pdf",
    namespace="support-center",
)

print(job.document_id)  # "doc_..."
```

For file uploads, the flow is the same except that you upload the file before
polling:

```python
job = client.jobs.create(
    source_type="file",
    file_name="manual.pdf",
    namespace="support-center",
)
client.jobs.upload(job, file=Path("manual.pdf"))
job_result = client.jobs.wait(job.job_id)
```

### Update an existing document

Pass the prior `document_id` to create an update job. If `namespace` is omitted,
the API resolves the namespace from the existing document.

```python
update_job = client.jobs.create(
    source_type="url",
    source_url="https://example.com/manual-v2.pdf",
    document_id=job.document_id,
)
```

The API rejects concurrent non-terminal jobs for the same document with a
retryable `ConflictError` using the server error code `ABORTED`.

### Query retrieval results

```python
response = client.retrieval.query(
    namespace="support-center",
    query="How do I pair a Bluetooth headset?",
    top_k=5,
)

for result in response.results:
    print(result.content)
    print(result.score)
    if result.citation:
        print(result.citation.source_file_name)
        print(result.citation.section_path)
```

Retrieval results expose `content`, not the older parse-result `text` field.
Media results may include `asset_url` when the server can sign the referenced
artifact.

### Exclude documents or sections

Use exclusions for follow-up queries that should avoid already-used context.

```python
response = client.retrieval.query(
    namespace="support-center",
    query="battery charging",
    top_k=10,
    exclude_document_ids=["doc_old"],
    exclude_sections=[
        {"document_id": "doc_123", "section_path": "Appendix / Legal"}
    ],
)
```

### List, get, and archive documents

```python
document_list = client.documents.list(namespace="support-center")
for document in document_list.documents:
    print(document.document_id, document.status, document.source_file_name)

document = client.documents.get("doc_123")
print(document.current_job_result_id)

archived = client.documents.archive("doc_123")
print(archived.status)  # "archived"
```

---

## Async Usage

Every method available on `Knowhere` has an async counterpart on `AsyncKnowhere`:

```python
import asyncio
import knowhere

async def main():
    async with knowhere.AsyncKnowhere(api_key="sk_...") as client:
        # Convenience method
        result = await client.parse(url="https://example.com/report.pdf")
        print(result.statistics.total_chunks)

        # Or step-by-step
        job = await client.jobs.create(
            source_type="url",
            source_url="https://example.com/report.pdf",
        )
        job_result = await client.jobs.wait(job.job_id)
        result = await client.jobs.load(job_result)

        retrieval = await client.retrieval.query(
            namespace="support-center",
            query="refund policy",
            top_k=5,
        )
        print(retrieval.results[0].content)

asyncio.run(main())
```

### Parallel parsing

```python
import asyncio
import knowhere

async def main():
    async with knowhere.AsyncKnowhere() as client:
        urls = [
            "https://example.com/doc1.pdf",
            "https://example.com/doc2.pdf",
            "https://example.com/doc3.pdf",
        ]
        results = await asyncio.gather(
            *(client.parse(url=u) for u in urls)
        )
        for r in results:
            print(f"{r.manifest.source_file_name}: {r.statistics.total_chunks} chunks")

asyncio.run(main())
```

---

## Progress Callbacks

### Upload progress

Called during file upload with `(bytes_sent, total_bytes)`. `total_bytes` may be `None` if the content length is unknown.

```python
def on_upload(bytes_sent: int, total_bytes: int | None) -> None:
    if total_bytes:
        pct = bytes_sent / total_bytes * 100
        print(f"Uploading: {pct:.1f}%")
    else:
        print(f"Uploaded: {bytes_sent} bytes")

result = client.parse(
    file=Path("report.pdf"),
    on_upload_progress=on_upload,
)
```

### Poll progress

Called on each poll iteration with `(job_result, elapsed_seconds)`:

```python
from knowhere.types.job import JobResult

def on_poll(job_result: JobResult, elapsed: float) -> None:
    progress = job_result.progress
    if isinstance(progress, float):
        print(f"Progress: {progress:.0%} ({elapsed:.0f}s)")
    else:
        print(f"Status: {job_result.status} ({elapsed:.0f}s)")

result = client.parse(
    url="https://example.com/report.pdf",
    on_poll_progress=on_poll,
)
```

---

## Error Handling

All errors inherit from `knowhere.KnowhereError`.

### Exception hierarchy

```
KnowhereError
├── APIConnectionError          # DNS, TCP, TLS failures
│   └── APITimeoutError         # Request exceeded timeout
├── APIStatusError              # HTTP 4xx/5xx responses
│   ├── BadRequestError         # 400
│   ├── AuthenticationError     # 401
│   ├── PaymentRequiredError    # 402
│   ├── PermissionDeniedError   # 403
│   ├── NotFoundError           # 404
│   ├── ConflictError           # 409
│   ├── RateLimitError          # 429 (auto-retried)
│   ├── InternalServerError     # 500 (auto-retried)
│   ├── ServiceUnavailableError # 502/503 (auto-retried)
│   └── GatewayTimeoutError     # 504 (auto-retried)
├── PollingTimeoutError         # Polling exceeded poll_timeout
├── JobFailedError              # Job reached "failed" status
└── ChecksumError               # SHA-256 mismatch on download
```

### Catching errors

```python
import knowhere

try:
    result = client.parse(url="https://example.com/report.pdf")
except knowhere.AuthenticationError:
    print("Invalid API key")
except knowhere.RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}s")
except knowhere.APIStatusError as e:
    print(f"HTTP {e.status_code}: {e.message}")
    print(f"Request ID: {e.request_id}")
except knowhere.PollingTimeoutError as e:
    print(f"Job {e.job_id} timed out after {e.elapsed:.0f}s")
except knowhere.JobFailedError as e:
    print(f"Job failed: [{e.code}] {e.message}")
except knowhere.ChecksumError as e:
    print(f"Checksum mismatch: expected {e.expected}, got {e.actual}")
except knowhere.APIConnectionError:
    print("Could not reach the API")
```

### APIStatusError fields

| Field | Type | Description |
|-------|------|-------------|
| `status_code` | `int` | HTTP status code |
| `code` | `str` | Error code from the API (e.g. `"invalid_api_key"`) |
| `message` | `str` | Human-readable error message |
| `request_id` | `str \| None` | Server request ID for support |
| `details` | `Any \| None` | Additional error details |
| `body` | `Any \| None` | Raw parsed response body |
| `response` | `httpx.Response` | The underlying HTTP response |

### Auto-retried errors

The following errors are automatically retried with exponential backoff (up to `max_retries` attempts):

- Connection errors and timeouts
- HTTP 408, 429, 500, 502, 503, 504
- Error codes: `rate_limit_exceeded`, `service_unavailable`, `gateway_timeout`, `internal_server_error`, `timeout`

---

## Configuration

### Constructor parameters

```python
client = knowhere.Knowhere(
    api_key="sk_...",                          # Required (or set KNOWHERE_API_KEY)
    base_url="https://api.knowhereto.ai",      # Default
    timeout=60.0,                              # HTTP request timeout (seconds)
    upload_timeout=600.0,                      # File upload timeout (seconds)
    max_retries=5,                             # Max retry attempts
    default_headers={"X-Custom": "value"},     # Extra headers on every request
)
```

### Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KNOWHERE_API_KEY` | API key (required) | — |
| `KNOWHERE_BASE_URL` | API base URL | `https://api.knowhereto.ai` |
| `KNOWHERE_LOG_LEVEL` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `WARNING` |

Priority: constructor argument > environment variable > default.

### Default values

| Setting | Default |
|---------|---------|
| `timeout` | 60s |
| `upload_timeout` | 600s (10 min) |
| `poll_interval` | 10s |
| `poll_timeout` | 1800s (30 min) |
| `max_retries` | 5 |
| `verify_checksum` | `True` |

### Context manager / resource cleanup

Both clients support context managers to ensure the underlying HTTP connection pool is properly closed:

```python
# Sync
with knowhere.Knowhere() as client:
    result = client.parse(url="https://example.com/report.pdf")

# Async
async with knowhere.AsyncKnowhere() as client:
    result = await client.parse(url="https://example.com/report.pdf")

# Manual cleanup
client = knowhere.Knowhere()
try:
    result = client.parse(url="https://example.com/report.pdf")
finally:
    client.close()
```

---

## Retries

Connection errors, timeouts, 429 Rate Limit, and 5xx server errors are automatically retried with exponential backoff.

```python
client = knowhere.Knowhere(
    max_retries=3,  # default is 5
)
```

The backoff formula is `min(0.5 * 2^attempt, 30s)` with 25% jitter. If the server returns a `Retry-After` header, that value is used instead.

To disable retries entirely:

```python
client = knowhere.Knowhere(max_retries=0)
```

---

## Logging

The SDK uses Python's standard `logging` module under the `"knowhere"` logger.

```python
import logging

# Enable debug logging
logging.getLogger("knowhere").setLevel(logging.DEBUG)
```

Or via environment variable:

```sh
export KNOWHERE_LOG_LEVEL=DEBUG
```

Log output format: `[LEVEL] knowhere: message`

At `DEBUG` level, the SDK logs every HTTP request and response (with API keys redacted).

---

## Supported File Formats

| Category | Extensions |
|----------|-----------|
| Documents | `.doc`, `.docx`, `.pdf`, `.txt` |
| Spreadsheets | `.xls`, `.xlsx`, `.csv` |
| Images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.svg` |
| Presentations | `.ppt`, `.pptx` |
| Markdown | `.md` |

Use the `doc_type` parsing parameter to override auto-detection:

```python
result = client.parse(
    file=Path("report.pdf"),
    parsing_params={"doc_type": "pdf"},
)
```

---

## Webhooks

Instead of polling, you can receive a webhook notification when a job completes.

### Setup

```python
job = client.jobs.create(
    source_type="url",
    source_url="https://example.com/report.pdf",
    webhook={"url": "https://your-server.com/webhook"},
)
```

### What the webhook receives

The API sends a POST request to your webhook URL with the `JobResult` payload as JSON. The request includes:

- `X-Knowhere-Signature` header — HMAC-SHA256 signature for verification
- The full job result in the request body

### Signature verification

```python
import hashlib
import hmac

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Retry behavior

If your webhook endpoint returns a non-2xx status code, the API retries delivery up to 6 times with exponential backoff.
