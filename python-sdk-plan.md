# Knowhere Python SDK — Implementation Plan

## Context

We are building a new Python SDK from scratch in `packages/sdk-python/`. The SDK is focused on **Developer Experience (DX)** as the #1 design principle. It wraps the Knowhere document parsing API, enabling developers to parse documents and get structured results (chunks, images, tables) as native Python objects.

The design follows patterns from **OpenAI Python SDK** (primary reference), **Cloudflare Python**, and **Boto3**, adapted to the Knowhere API's document parsing workflow.

Current scope: **Document parsing** — the complete flow from submitting a document (URL or file) to receiving structured parse results with text chunks, images, and tables.

---

## 1. Public API Design — How Callers Use It

### 1.1 One-Liner: Parse a URL

```python
import knowhere

client = knowhere.Knowhere(api_key="sk_...")
result = client.parse(url="https://example.com/report.pdf")

print(result.manifest.statistics.total_chunks)  # 152
for chunk in result.text_chunks:
    print(chunk.content[:80])
```

### 1.2 One-Liner: Parse a Local File

```python
from pathlib import Path

result = client.parse(
    file=Path("report.pdf"),
    model="advanced",
    ocr=True,
)

# Access structured results directly
print(result.manifest.source_file_name)   # "report.pdf"
print(len(result.chunks))                  # 152
print(result.manifest.statistics)          # Statistics(total_chunks=152, ...)
```

### 1.3 Access Different Chunk Types

```python
result = client.parse(url="https://example.com/report.pdf")

# Text chunks — content + keywords + summary
for chunk in result.text_chunks:
    print(chunk.path)                # "Default_Root/bitcoin.pdf-->1. Introduction"
    print(chunk.keywords)            # ["electronic payment system", ...]
    print(chunk.summary)             # "An electronic payment system..."
    print(chunk.tokens)              # 450
    print(chunk.relationships)       # ["IMAGE_271ae087-...", ...]

# Image chunks — metadata + raw bytes
for chunk in result.image_chunks:
    print(chunk.file_path)           # "images/image-0-## 1. Intr.jpg"
    print(chunk.summary)             # "image-0-## 1. Intr0"
    print(len(chunk.data))           # 44005 (bytes)

    # Save image to disk
    chunk.save("./output/")          # writes to ./output/image-0-## 1. Intr.jpg

# Table chunks — metadata + HTML content
for chunk in result.table_chunks:
    print(chunk.file_path)           # "tables/TABLE_fa7e0e7f-...html"
    print(chunk.table_type)          # "market_data"
    print(chunk.html[:100])          # "<table><tr><td>总股本...</td>..."
```

### 1.4 Save All Results to Disk

```python
result = client.parse(file=Path("report.pdf"))

# Save everything to a directory (mirrors ZIP structure)
result.save("./output/report/")
# Creates:
#   ./output/report/manifest.json
#   ./output/report/chunks.json
#   ./output/report/full.md
#   ./output/report/hierarchy.json
#   ./output/report/kb.csv
#   ./output/report/images/image-0-## 1. Intr.jpg
#   ./output/report/tables/TABLE_fa7e0e7f-...html  (if any)
```

### 1.5 Step-by-Step Control (Granular)

```python
# Step 1: Create a parsing job
job = client.jobs.create(
    source_type="file",
    file_name="report.pdf",
    parsing_params={"model": "advanced", "ocr_enabled": True},
)

# Step 2: Upload file to presigned URL (streaming, safe for large files)
client.jobs.upload(job, file=Path("report.pdf"))

# Step 3: Poll until done (adaptive backoff)
job_result = client.jobs.wait(job.job_id, poll_interval=10.0, poll_timeout=1800.0)

# Step 4: Download and parse results into Python objects
result = client.jobs.load(job_result)
print(result.manifest.statistics)
```

### 1.6 Async Usage

```python
import asyncio
import knowhere

async def main():
    async with knowhere.AsyncKnowhere(api_key="sk_...") as client:
        result = await client.parse(url="https://example.com/report.pdf")
        print(result.manifest.statistics.total_chunks)

        for chunk in result.text_chunks:
            print(chunk.summary)

asyncio.run(main())
```

### 1.7 Error Handling

```python
from knowhere import (
    Knowhere,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    BadRequestError,
    APIStatusError,
    PollingTimeoutError,
)

try:
    result = client.parse(url="https://example.com/report.pdf")
except BadRequestError as e:
    print(e.status_code)   # 400
    print(e.code)          # "INVALID_ARGUMENT"
    print(e.message)       # "Unsupported file format"
    print(e.request_id)    # "req_abc123"
except NotFoundError as e:
    print(e.message)       # "Job not found"
except RateLimitError as e:
    print(e.retry_after)   # 15 (seconds)
except AuthenticationError:
    print("Invalid API key")
except PollingTimeoutError:
    print("Job did not complete within timeout")
except APIStatusError as e:
    print(f"API error {e.status_code}: {e.message}")
```

### 1.8 Environment Variable Configuration

```python
# Auto-detected env vars (no constructor args needed):
#   KNOWHERE_API_KEY   → api_key
#   KNOWHERE_BASE_URL  → base_url (default: https://api.knowhereto.ai)

client = knowhere.Knowhere()  # uses env vars
```

### 1.9 Context Manager

```python
# Sync — ensures httpx.Client is properly closed
with knowhere.Knowhere(api_key="sk_...") as client:
    result = client.parse(url="https://example.com/report.pdf")

# Async — ensures httpx.AsyncClient is properly closed
async with knowhere.AsyncKnowhere(api_key="sk_...") as client:
    result = await client.parse(url="https://example.com/report.pdf")
```

---

## 2. Detailed SDK API Design

### 2.1 Client Constructors

```python
class Knowhere:
    """Synchronous Knowhere client."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 60.0,      # Per-request HTTP timeout (API calls)
        upload_timeout: float | httpx.Timeout = 600.0,  # Per-request HTTP timeout (file upload, default 10min)
        max_retries: int = 5,
        default_headers: dict[str, str] | None = None,
    ) -> None: ...

    # Resource namespaces
    @cached_property
    def jobs(self) -> Jobs: ...

    # Context manager
    def __enter__(self) -> Self: ...
    def __exit__(self, *args) -> None: ...
    def close(self) -> None: ...


class AsyncKnowhere:
    """Asynchronous Knowhere client."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 60.0,
        upload_timeout: float | httpx.Timeout = 600.0,
        max_retries: int = 5,
        default_headers: dict[str, str] | None = None,
    ) -> None: ...

    @cached_property
    def jobs(self) -> AsyncJobs: ...

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, *args) -> None: ...
    async def close(self) -> None: ...
```

**Constructor resolution order (highest → lowest):**
1. Constructor arguments (`api_key=`, `base_url=`)
2. Environment variables (`KNOWHERE_API_KEY`, `KNOWHERE_BASE_URL`)
3. Defaults (`base_url="https://api.knowhereto.ai"`, `timeout=60.0`, `upload_timeout=600.0`, `max_retries=5`)

If `api_key` is not found via arg or env, raises `KnowhereError("Missing API key...")`.

### 2.2 High-Level Parsing Methods (on Client)

The `parse()` method is the **primary entry point** — it handles the entire flow (create job → upload if file → poll → load result ZIP into memory → parse → return).

The method uses `@overload` to enforce `file_name` requirements at type-check time — VS Code / mypy / pyright will show errors before the code runs:

```python
# Shared params used by all overloads (defined here for brevity, not actual code)
# model, ocr, doc_type, smart_title_parse, summary_image, summary_table, summary_text,
# data_id, poll_interval, poll_timeout, on_upload_progress, on_poll_progress, webhook_url

class Knowhere:

    # Overload 1: Parse from URL — no file, no file_name
    @overload
    def parse(
        self,
        *,
        url: str,
        model: Literal["base", "advanced"] = ...,
        ocr: bool = ...,
        doc_type: Literal["auto", "pdf", "docx", "txt", "md"] = ...,
        # ... other shared params ...
    ) -> ParseResult: ...

    # Overload 2: Parse from Path — file_name optional (inferred from Path.name)
    @overload
    def parse(
        self,
        *,
        file: Path,
        file_name: str | None = None,
        model: Literal["base", "advanced"] = ...,
        ocr: bool = ...,
        doc_type: Literal["auto", "pdf", "docx", "txt", "md"] = ...,
        # ... other shared params ...
    ) -> ParseResult: ...

    # Overload 3: Parse from bytes — file_name REQUIRED
    @overload
    def parse(
        self,
        *,
        file: bytes,
        file_name: str,                        # mandatory — no way to infer
        model: Literal["base", "advanced"] = ...,
        ocr: bool = ...,
        doc_type: Literal["auto", "pdf", "docx", "txt", "md"] = ...,
        # ... other shared params ...
    ) -> ParseResult: ...

    # Overload 4: Parse from BinaryIO — file_name REQUIRED
    @overload
    def parse(
        self,
        *,
        file: BinaryIO,
        file_name: str,                        # mandatory — .name is unreliable
        model: Literal["base", "advanced"] = ...,
        ocr: bool = ...,
        doc_type: Literal["auto", "pdf", "docx", "txt", "md"] = ...,
        # ... other shared params ...
    ) -> ParseResult: ...

    # Implementation signature (not visible to type checkers)
    def parse(
        self,
        *,
        url: str | None = None,
        file: Path | BinaryIO | bytes | None = None,
        file_name: str | None = None,

        # Parsing options
        model: Literal["base", "advanced"] = "base",
        ocr: bool = False,
        doc_type: Literal["auto", "pdf", "docx", "txt", "md"] = "auto",
        smart_title_parse: bool = True,
        summary_image: bool = True,
        summary_table: bool = True,
        summary_text: bool = True,

        # Identification
        data_id: str | None = None,

        # Polling control
        poll_interval: float = 10.0,
        poll_timeout: float = 1800.0,

        # Progress callbacks
        on_upload_progress: UploadProgressCallback | None = None,
        on_poll_progress: PollProgressCallback | None = None,

        # Webhook
        webhook_url: str | None = None,
    ) -> ParseResult: ...
```

**Type-check behavior:**
```python
# OK — url, no file_name needed
client.parse(url="https://example.com/report.pdf")

# OK — Path, file_name inferred
client.parse(file=Path("report.pdf"))

# OK — Path with explicit file_name override
client.parse(file=Path("report.pdf"), file_name="custom_name.pdf")

# ERROR at type-check time — bytes without file_name
client.parse(file=b"...", model="advanced")  # mypy/pyright: missing file_name

# ERROR at type-check time — BinaryIO without file_name
client.parse(file=open("report.pdf", "rb"))  # mypy/pyright: missing file_name

# OK — BinaryIO with file_name
client.parse(file=open("report.pdf", "rb"), file_name="report.pdf")
```

**Behavior:**
1. Validates inputs: exactly one of `url` / `file` must be provided; `file_name` inferred from `Path` or required for `BinaryIO`/`bytes`.
2. Creates job via `POST /v1/jobs`.
3. If `file` is provided: streams file to presigned URL.
4. Polls `GET /v1/jobs/{job_id}` with adaptive backoff until `done` or `failed`.
5. If `failed`: raises `JobFailedError` with the embedded error from the API.
6. Downloads ZIP from `result_url`, verifies SHA-256 checksum.
7. Unzips and parses contents into `ParseResult`.
8. Returns `ParseResult`.

**Async equivalent:**
```python
class AsyncKnowhere:
    async def parse(self, *, ...) -> ParseResult: ...
    # Same signature as Knowhere.parse()
```

### 2.3 Jobs Resource — Low-Level Methods

All methods under `client.jobs.*`. These map 1:1 to API endpoints plus convenience helpers.

#### `jobs.create()` — Create a parsing job

```python
def create(
    self,
    *,
    source_type: Literal["file", "url"],
    source_url: str | None = None,             # Required when source_type="url"
    file_name: str | None = None,              # Required when source_type="file"
    data_id: str | None = None,
    parsing_params: ParsingParams | dict | None = None,
    webhook: WebhookConfig | dict | None = None,
) -> Job:
    """
    Create a new parsing job.

    POST /v1/jobs

    Returns a Job object. For file uploads, the Job contains
    upload_url and upload_headers for the next step.
    """
```

#### `jobs.get()` — Get job status and result

```python
def get(
    self,
    job_id: str,
) -> JobResult:
    """
    Retrieve current job status and result details.

    GET /v1/jobs/{job_id}
    """
```

#### `jobs.upload()` — Upload file to presigned URL

```python
def upload(
    self,
    job: Job | str,
    *,
    file: Path | BinaryIO | bytes,
    on_progress: UploadProgressCallback | None = None,
) -> None:
    """
    Stream a file to the job's presigned upload URL.

    Uses HTTP PUT to the presigned S3 URL from job.upload_url.
    Streams from disk when given a Path — never loads entire
    file into memory. Safe for files of any size.

    If `job` is a string, it is treated as a job_id and the
    job is fetched first to obtain upload_url.

    Retry behavior by file type:
    - Path: safe to retry — SDK reopens the file from disk on each attempt.
    - bytes: safe to retry — immutable, reusable across attempts.
    - BinaryIO (seekable): safe to retry — SDK calls seek(0) before each attempt.
    - BinaryIO (non-seekable, e.g. stdin, pipes, generators): NOT retryable.
      If the PUT fails and the stream is not seekable, raises
      KnowhereError("Cannot retry upload: file stream is not seekable.
      Use Path or bytes instead.") instead of silently corrupting the upload.
      Non-seekable streams are passed to save memory — buffering them
      into bytes would defeat that purpose.
    """
```

#### `jobs.wait()` — Poll until terminal state

```python
def wait(
    self,
    job_id: str,
    *,
    poll_interval: float = 10.0,
    poll_timeout: float = 1800.0,
    on_progress: PollProgressCallback | None = None,
) -> JobResult:
    """
    Poll job status until it reaches a terminal state (done/failed).

    Uses adaptive backoff: starts at poll_interval, increases
    by 1.2x after 60s elapsed, capped at 30s per interval.

    Raises:
        PollingTimeoutError: If job doesn't complete within poll_timeout.
        JobFailedError: If job reaches 'failed' status.
    """
```

#### `jobs.load()` — Load result ZIP into Python objects

```python
def load(
    self,
    job_result: JobResult | str,
    *,
    verify_checksum: bool = True,
) -> ParseResult:
    """
    Fetch the result ZIP, verify checksum, unzip in memory,
    and load contents into a ParseResult object.

    If `job_result` is a string, it is treated as a job_id and
    the job is fetched first to obtain result_url.

    Raises:
        ChecksumError: If SHA-256 verification fails.
        ValueError: If job is not in 'done' status.
    """
```

### 2.4 Async Counterparts

Every sync method has an identical async counterpart on `AsyncJobs`:

```python
class AsyncJobs:
    async def create(self, ...) -> Job: ...
    async def get(self, job_id: str) -> JobResult: ...
    async def upload(self, job: Job | str, *, file: ...) -> None: ...
    async def wait(self, job_id: str, ...) -> JobResult: ...
    async def load(self, job_result: JobResult | str, ...) -> ParseResult: ...
```

### 2.5 Method Summary Table

| Method |  What It Does | Returns |
|--------|-------|-------------|---------|
| `client.parse(url=\|file=)` |  Complete parsing flow in one call | `ParseResult` |
| `client.jobs.create(...)` | Create a job | `Job` |
| `client.jobs.get(job_id)` |  Get job status/result | `JobResult` |
| `client.jobs.upload(job, file=)` |  Stream file to presigned URL | `None` |
| `client.jobs.wait(job_id)` |  Poll until terminal state | `JobResult` |
| `client.jobs.load(job_result)` |  Load result ZIP into `ParseResult` | `ParseResult` |

---

## 3. Result Types — Python Objects from ZIP

### 3.1 ParseResult — Top-Level Container

```python
class ParseResult:
    """
    Complete parsing result. Contains all extracted content
    from a document: text chunks, images, tables, and metadata.

    Constructed by loading and unpacking the result ZIP file into memory.
    """

    manifest: Manifest
    chunks: list[Chunk]
    full_markdown: str | None          # Content of full.md (full Markdown), None if not present
    hierarchy: dict | None             # Content of hierarchy.json (document structure), None if not present
    raw_zip: bytes                     # The original ZIP bytes (for re-saving or custom processing)

    @property
    def text_chunks(self) -> list[TextChunk]:
        """All chunks with type='text'."""

    @property
    def image_chunks(self) -> list[ImageChunk]:
        """All chunks with type='image', each carrying raw image bytes."""

    @property
    def table_chunks(self) -> list[TableChunk]:
        """All chunks with type='table', each carrying HTML content."""

    @property
    def job_id(self) -> str:
        """Shortcut for self.manifest.job_id."""

    @property
    def statistics(self) -> Statistics:
        """Shortcut for self.manifest.statistics."""

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        """Find a chunk by its ID. Returns None if not found."""

    def save(self, directory: str | Path) -> Path:
        """
        Save all result files to a directory, mirroring the ZIP structure:
            directory/
            ├── manifest.json
            ├── chunks.json
            ├── full.md
            ├── hierarchy.json
            ├── kb.csv
            ├── images/image-0-xxx.jpg
            └── tables/TABLE_xxx.html

        Returns the Path to the output directory.
        """
```

### 3.2 Manifest

```python
class Manifest(BaseModel):
    """ZIP package index and metadata (from manifest.json)."""

    version: str                        # Schema version, e.g. "1.0"
    job_id: str
    data_id: str | None
    source_file_name: str               # Original uploaded file name
    processing_date: datetime
    statistics: Statistics
    files: FileIndex


class Statistics(BaseModel):
    total_chunks: int
    text_chunks: int
    image_chunks: int
    table_chunks: int
    total_pages: int | None = None


class FileIndex(BaseModel):
    """Index of all files in the ZIP package."""

    chunks: str                         # Filename, always "chunks.json"
    markdown: str | None = None         # Filename, e.g. "full.md" or None
    kb_csv: str | None = None           # Filename, e.g. "kb.csv" or None
    hierarchy: str | None = None        # Filename, e.g. "hierarchy.json" or None
    images: list[ImageFileInfo]
    tables: list[TableFileInfo]


class ImageFileInfo(BaseModel):
    id: str                             # UUID, e.g. "1c4e5e0e-127b-56d4-..."
    file_path: str                      # e.g. "images/image-0-## 1. Intr.jpg"
    size_bytes: int
    format: str                         # "jpg", "png", etc.
    width: int | None = None
    height: int | None = None


class TableFileInfo(BaseModel):
    id: str                             # UUID or prefixed ID
    file_path: str                      # e.g. "tables/TABLE_fa7e0e7f-...html"
    size_bytes: int
    format: str                         # Always "html"
```

### 3.3 Chunk Types

```python
Chunk = TextChunk | ImageChunk | TableChunk
```

All chunk types share a common base:

```python
class BaseChunk(BaseModel):
    """Base class for all chunk types."""

    chunk_id: str                       # UUID, e.g. "4fb09ea6-1dea-56b1-..."
    type: Literal["text", "image", "table"]
    content: str                        # Text content or description
    path: str                           # Document path, e.g. "Default_Root/bitcoin.pdf-->1. Introduction"


class TextChunk(BaseChunk):
    """A text chunk extracted from the document."""

    type: Literal["text"] = "text"

    # Metadata
    length: int                         # Character count of content
    tokens: int | None = None           # Token count (for LLM context budgeting)
    keywords: list[str] | None = None   # Extracted keywords
    summary: str | None = None          # AI-generated summary
    relationships: list[str] | None = None  # Related chunk IDs (images/tables)


class ImageChunk(BaseChunk):
    """An image chunk extracted from the document, with raw image bytes."""

    type: Literal["image"] = "image"

    # Metadata
    length: int                         # Character count of content (description)
    file_path: str                      # Path within ZIP, e.g. "images/image-0-## 1. Intr.jpg"
    summary: str | None = None          # AI-generated description

    # Image data (loaded from ZIP)
    data: bytes                         # Raw image file bytes

    @property
    def format(self) -> str:
        """Image format derived from file_path extension (e.g. 'jpg', 'png')."""

    def save(self, directory: str | Path) -> Path:
        """
        Save image to directory using the filename from file_path.
        Returns the path to the saved file.

        Example:
            chunk.save("./output/")  # → ./output/image-0-## 1. Intr.jpg
        """


class TableChunk(BaseChunk):
    """A table chunk extracted from the document, with HTML content."""

    type: Literal["table"] = "table"

    # Metadata
    length: int                         # Character count of content (description)
    file_path: str                      # Path within ZIP, e.g. "tables/TABLE_xxx.html"
    table_type: str | None = None       # Semantic type, e.g. "market_data"
    summary: str | None = None          # AI-generated description

    # Table data (loaded from ZIP)
    html: str                           # Raw HTML content of the table

    def save(self, directory: str | Path) -> Path:
        """
        Save table HTML to directory using the filename from file_path.
        Returns the path to the saved file.
        """
```

### 3.4 Job Types (API Response Models)

```python
class Job(BaseModel):
    """Response from POST /v1/jobs (job creation)."""

    job_id: str
    status: Literal["pending", "waiting-file", "running", "converting", "done", "failed"]
    source_type: str
    data_id: str | None = None
    created_at: datetime

    # File upload fields (only present when source_type="file")
    upload_url: str | None = None
    upload_headers: dict[str, str] | None = None
    expires_in: int | None = None


class JobResult(BaseModel):
    """Response from GET /v1/jobs/{job_id} (job status + result)."""

    job_id: str
    status: Literal["pending", "waiting-file", "running", "converting", "done", "failed"]
    source_type: str
    data_id: str | None = None
    created_at: datetime
    progress: dict[str, Any] | None = None

    # Error (only when status="failed")
    error: JobError | None = None

    # Result (only when status="done")
    result: dict[str, Any] | None = None
    result_url: str | None = None
    result_url_expires_at: datetime | None = None

    # Extended metadata
    file_name: str | None = None
    file_extension: str | None = None
    model: str | None = None
    ocr_enabled: bool | None = None
    duration_seconds: float | None = None
    credits_spent: float | None = None

    @property
    def is_terminal(self) -> bool:
        """True if status is 'done' or 'failed'."""

    @property
    def is_done(self) -> bool:
        """True if status is 'done'."""

    @property
    def is_failed(self) -> bool:
        """True if status is 'failed'."""


class JobError(BaseModel):
    """Embedded error in a failed job result."""

    code: str
    message: str
    request_id: str
    details: dict[str, Any] | None = None
```

### 3.5 Request Parameter Types

```python
class ParsingParams(TypedDict, total=False):
    """Parsing configuration parameters."""

    model: Literal["base", "advanced"]
    ocr_enabled: bool
    kb_dir: str
    doc_type: Literal["auto", "pdf", "docx", "txt", "md"]
    smart_title_parse: bool
    summary_image: bool
    summary_table: bool
    summary_txt: bool
    add_frag_desc: str


class WebhookConfig(TypedDict, total=False):
    """Webhook notification configuration."""

    url: str
```

### 3.6 Progress Callback Types

The SDK exposes progress via simple callbacks — no extra dependencies required. Users can hook in `tqdm`, `rich`, or any custom UI.

```python
# Type aliases defined in _types.py

UploadProgressCallback = Callable[[int, int | None], None]
"""
Called during file upload with (bytes_sent, total_bytes).
total_bytes is None when the file size is unknown (non-seekable BinaryIO).

Usage with tqdm:
    from tqdm import tqdm

    bar = tqdm(total=Path("report.pdf").stat().st_size, unit="B", unit_scale=True)
    client.jobs.upload(job, file=Path("report.pdf"), on_progress=bar.update)
    bar.close()
"""


PollProgressCallback = Callable[[JobResult, float], None]
"""
Called after each poll with (job_result, elapsed_seconds).
Allows displaying status transitions and elapsed time.

Usage with print:
    def show_status(job_result: JobResult, elapsed: float) -> None:
        print(f"[{elapsed:.0f}s] Status: {job_result.status}")

    client.jobs.wait(job_id, on_progress=show_status)

Usage with rich:
    from rich.console import Console
    console = Console()

    def show_status(job_result: JobResult, elapsed: float) -> None:
        console.print(f"[bold]{job_result.status}[/bold] ({elapsed:.0f}s)")

    result = client.parse(url="...", on_poll_progress=show_status)
"""
```

**Design decisions:**
- **Callbacks, not dependency injection** — `Callable` is stdlib, no protocol classes needed. Users pass a simple function or lambda.
- **`UploadProgressCallback` receives `(bytes_sent, total_bytes)`** — `bytes_sent` is the incremental chunk size (matches `tqdm.update()` semantics), not cumulative. `total_bytes` is `None` for non-seekable streams where the size is unknown.
- **`PollProgressCallback` receives `(job_result, elapsed_seconds)`** — the full `JobResult` is passed so the user can inspect status, progress, and any other fields. `elapsed` is wall-clock seconds since polling started.
- **No built-in progress bar** — keeps the dependency list at zero. Users who want visual feedback bring their own library (tqdm, rich, click).

---

## 4. Project Structure

```
packages/sdk-python/
├── pyproject.toml
├── uv.lock                              # Lockfile for reproducible dev environments (git-tracked)
├── src/
│   └── knowhere/
│       ├── __init__.py                   # Public API: Knowhere, AsyncKnowhere, exceptions, types
│       ├── py.typed                      # PEP 561 marker — ships inline types
│       ├── _version.py                   # __version__ = "0.1.0"
│       ├── _constants.py                 # DEFAULT_BASE_URL, ENV var names, timeouts
│       ├── _types.py                     # NotGiven sentinel, Omit, Headers, Query aliases
│       ├── _exceptions.py                # Full exception hierarchy
│       ├── _base_client.py               # Shared HTTP logic: auth, retry, error parsing
│       ├── _client.py                    # Knowhere(SyncAPIClient), AsyncKnowhere(AsyncAPIClient)
│       ├── _response.py                  # APIResponse wrapper (for raw response access)
│       ├── _logging.py                   # Logger setup, sensitive header filtering
│       ├── types/
│       │   ├── __init__.py               # Re-exports all types
│       │   ├── job.py                    # Job, JobResult, JobError
│       │   ├── result.py                 # ParseResult, Manifest, Chunk types, Statistics, etc.
│       │   ├── params.py                 # ParsingParams, WebhookConfig TypedDicts
│       │   └── shared.py                 # Shared models
│       ├── resources/
│       │   ├── __init__.py               # Re-exports Jobs, AsyncJobs
│       │   ├── _base.py                  # SyncAPIResource / AsyncAPIResource
│       │   └── jobs.py                   # Jobs (sync) + AsyncJobs (async)
│       └── lib/
│           ├── __init__.py
│           ├── polling.py                # Adaptive polling loop (sync + async)
│           ├── upload.py                 # Streaming file upload to presigned URL
│           └── result_parser.py          # ZIP loading, checksum verification, parsing into ParseResult
├── tests/
│   ├── conftest.py                       # Fixtures: mock client, respx mock API
│   ├── test_client.py                    # Client init, config, env vars, context manager
│   ├── test_exceptions.py               # Error parsing, status→exception mapping
│   ├── test_models.py                   # Pydantic model serialization/deserialization
│   ├── test_jobs.py                     # Jobs resource: create, get, upload, wait, load
│   ├── test_parse.py                    # High-level parse() method (URL + file flows)
│   ├── test_polling.py                  # Polling logic, adaptive interval, timeout
│   ├── test_upload.py                   # File upload streaming
│   ├── test_result_parser.py            # ZIP → ParseResult parsing, checksum verification
│   ├── test_retry.py                    # Retry logic: 429/503/504, backoff, max retries
│   └── test_logging.py                  # Sensitive header filtering
└── examples/
    ├── parse_url.py                      # Parse document from URL
    ├── parse_file.py                     # Parse local file
    ├── step_by_step.py                   # Granular control with jobs.*
    ├── async_usage.py                    # Async client usage
    └── error_handling.py                 # Exception handling patterns
```

---

## 5. Client Architecture

### Class Hierarchy

```
BaseClient                              # Config resolution, auth headers, error parsing, retry
├── SyncAPIClient(BaseClient)           # httpx.Client — _request() with retry loop
│   └── Knowhere                        # Public sync client; owns .jobs, exposes .parse()
└── AsyncAPIClient(BaseClient)          # httpx.AsyncClient — async _request() with retry loop
    └── AsyncKnowhere                   # Public async client; owns .jobs, exposes .parse()

SyncAPIResource                         # Base for sync resources
└── Jobs                                # client.jobs.* (create, get, upload, wait, load)

AsyncAPIResource                        # Base for async resources
└── AsyncJobs                           # async counterpart
```

### Key Design Decisions

1. **Two separate client classes** (not one dual-mode class). Using `asyncio.run()` wrappers for sync-from-async breaks inside existing event loops. Separate `httpx.Client` / `httpx.AsyncClient` is the correct approach, following OpenAI/Cloudflare SDKs.

2. **`client.parse()` delegates to `client.jobs`** — the top-level method is syntactic sugar that calls `create` → `upload` (if file) → `wait` → `load` internally.

3. **Resource namespaces** (`client.jobs.create()`) — follows OpenAI pattern, better IDE discoverability than flat methods.

4. **`NotGiven` sentinel** — distinguishes "not provided" from `None`. Critical for optional params where `None` has semantic meaning.

5. **Context manager support** — `with Knowhere(...) as client:` and `async with AsyncKnowhere(...) as client:` for proper HTTP client cleanup.

6. **Result auto-loading** — the high-level `parse()` method automatically fetches the result ZIP, verifies checksum, unzips, and returns `ParseResult`. Low-level users can call `jobs.load()` separately.

---

## 6. Exception Hierarchy

The SDK defines its own exception hierarchy in `_exceptions.py`. These are **SDK-specific, developer-facing names** — they do NOT reuse or expose any server-side exception class names.

### Design Principles

- **No server internals leaked**: Uses standard HTTP-semantic names (`BadRequestError`, `NotFoundError`)
- **Flat import**: `from knowhere import NotFoundError`
- **Catch-all base class**: `KnowhereError` catches everything; `APIStatusError` catches all HTTP errors
- **Rich context**: Every API exception carries `status_code`, `code`, `message`, `request_id`, `details`, `body`, `response`
- **No dependency on server packages**: Standalone — never imports from `shared-python`

### Hierarchy

```
Exception
└── KnowhereError                          # Base for ALL SDK errors
    ├── APIConnectionError                 # Network/DNS/TLS failure (no HTTP response)
    │   └── APITimeoutError                # Request timed out before response
    ├── PollingTimeoutError                # Job poll exceeded timeout
    ├── JobFailedError                     # Job completed with status='failed'
    │   ├── code: str                      # Error code from job result
    │   ├── message: str                   # Error message
    │   └── job_result: JobResult          # Full job result for inspection
    ├── ChecksumError                      # SHA-256 verification failed on downloaded ZIP
    └── APIStatusError                     # HTTP 4xx/5xx (got a response with error status)
        ├── BadRequestError                # 400 — validation errors, bad input
        ├── AuthenticationError            # 401 — missing or invalid API key
        ├── PaymentRequiredError           # 402 — insufficient credits
        ├── PermissionDeniedError          # 403 — caller lacks access
        ├── NotFoundError                  # 404 — resource doesn't exist
        ├── ConflictError                  # 409 — resource conflict
        ├── RateLimitError                 # 429 — rate limit exceeded (has retry_after)
        ├── InternalServerError            # 500 — server-side failure
        ├── ServiceUnavailableError        # 502/503 — service temporarily down
        └── GatewayTimeoutError            # 504 — upstream timeout
```

### APIStatusError Attributes

```python
class APIStatusError(KnowhereError):
    status_code: int              # HTTP status code
    code: str | None              # API error code from response body (e.g. "NOT_FOUND")
    message: str                  # Human-readable error message
    request_id: str | None        # Request ID for debugging
    details: dict | None          # Structured details (violations, retry_after, etc.)
    body: dict | None             # Full parsed JSON response body
    response: httpx.Response      # Raw httpx response
```

`RateLimitError`, `ServiceUnavailableError`, and `GatewayTimeoutError` additionally expose:
```python
    retry_after: float | None     # Seconds to wait before retry
```

### Server Error Code → SDK Exception Mapping

HTTP status codes determine which exception is raised. The `error.code` from the response is stored as `e.code` but does not affect exception class selection:

```python
_STATUS_TO_EXCEPTION = {
    400: BadRequestError,
    401: AuthenticationError,
    402: PaymentRequiredError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
    500: InternalServerError,
    502: ServiceUnavailableError,
    503: ServiceUnavailableError,
    504: GatewayTimeoutError,
}
```

### Retryable Errors (auto-retry by client)

- **409** (ConflictError when `code == "ABORTED"`) — retry immediately
- **503** (ServiceUnavailableError) — retry with backoff
- **504** (GatewayTimeoutError) — retry with backoff
- **429** (RateLimitError) — retry ONLY if `retry_after` is present; NO retry if quota exceeded
- **Connection/timeout errors** — retry with backoff

---

## 7. Result Parsing Pipeline

### 7.1 ZIP Download & Verification Flow

```
JobResult.result_url ──GET──→ ZIP bytes
                                │
                          SHA-256 verify against API response checksum
                                │
                          zipfile.ZipFile (in-memory via io.BytesIO)
                                │
                    ┌───────────┼──────────┬──────────────┐
                    │           │          │              │
              manifest.json  chunks.json  full.md    hierarchy.json
                    │           │          │              │
              Manifest()   parse chunks  str | None  dict | None
                           + load assets
                                │
                    ┌───────────┼──────────────┐
                    │                          │
              images/*.jpg               tables/*.html
              → ImageChunk.data          → TableChunk.html
                    │                          │
                    └──────────┬───────────────┘
                               │
                         ParseResult()
```

### 7.2 Implementation Notes

1. **In-memory processing**: ZIP is downloaded to `io.BytesIO`, not disk. For very large results, the SDK streams the download and processes in memory. No temp files created.

2. **Checksum verification**: After downloading the full ZIP, compute SHA-256 and compare against the checksum from the API response. If mismatch, raise `ChecksumError`.

3. **Chunk loading**: Parse `chunks.json`, then for each image/table chunk, read the corresponding file from the ZIP and attach as `.data` (images) or `.html` (tables).

4. **Path sanitization & Zip Slip prevention**: The SDK must **never trust paths inside the ZIP blindly**. Both `load()` (when reading ZIP entries) and `save()` (when writing to disk) apply strict sanitization:

   **During `load()` — reading from ZIP**:
   - Reject any ZIP entry whose resolved path escapes the expected structure (e.g., `../../etc/passwd`, `../../../Windows/System32/config`). Specifically: after normalizing with `os.path.normpath()`, reject if the path starts with `..` or is absolute. This prevents [Zip Slip](https://security.snyk.io/research/zip-slip-vulnerability) attacks.
   - Only process entries under known prefixes: root-level files (`manifest.json`, `chunks.json`, `full.md`, `hierarchy.json`, `kb.csv`) and known directories (`images/`, `tables/`). Ignore unexpected entries.
   - Log a warning for any rejected or unexpected entries at DEBUG level.

   **During `save()` — writing to disk**:
   - Sanitize filenames for cross-platform compatibility before writing:
     - Replace Windows-illegal characters (`:`, `?`, `*`, `"`, `<`, `>`, `|`) with `_`
     - Strip leading/trailing whitespace and dots from filenames
     - Truncate individual filename components to 200 characters (well under Windows' 255 limit, leaves room for the directory path)
     - Resolve the final write path and verify it is a descendant of the user-specified output directory — reject if it escapes (defense-in-depth against any sanitization bypass)
   - Preserve the original filename in the `Manifest` / chunk metadata so the user can see what the server intended, even if the on-disk name differs.
   - Use `pathlib.Path` throughout for consistent cross-platform path handling.

5. **Eager vs lazy loading**: All data is loaded eagerly when `load()` is called. `ParseResult` is a fully self-contained, immutable snapshot with no deferred I/O.

   **Why eager for v1**: Document parsing results are bounded in size (typically a few MB of images per PDF, not GB). The ZIP is already fully in memory after the HTTP fetch, so deferring reads from an in-memory `ZipFile` saves almost nothing. Eager loading gives us:
   - Simple mental model — `ParseResult` is a plain data object, safe to pass around, cache, serialize, or inspect in a debugger
   - No resource lifetime issues — no "connection closed" or "file handle expired" errors when accessing `.data` later
   - Thread-safe and async-safe by default — no hidden I/O on attribute access
   - Predictable memory usage — all allocation happens in one place (`load()`), easy to profile

   **Side effects of lazy loading (why we avoid it for now)**:
   - `ParseResult` becomes **stateful** — it holds a reference to the `ZipFile` handle or raw ZIP bytes, and accessing `.data` / `.html` triggers I/O. This makes the object's behavior depend on *when* you read it, not just *what* it contains.
   - **Resource lifecycle coupling** — the `ZipFile` (or underlying `BytesIO`) must stay alive as long as any chunk's `.data` hasn't been accessed yet. If the user stores `ParseResult` but the backing buffer is garbage-collected or explicitly closed, subsequent `.data` access raises `ValueError: I/O operation on closed file`.
   - **Thread/async safety breaks** — concurrent access to `.data` from multiple threads could trigger simultaneous `ZipFile.read()` calls, which is not thread-safe. In async contexts, a lazy `.data` property would block the event loop with synchronous I/O.
   - **Unpredictable performance** — first access to `chunk.data` is slow (decompression), subsequent accesses may or may not be cached. This makes profiling and latency prediction harder.
   - **Serialization breaks** — `pickle`, `json`, or sending `ParseResult` across process boundaries fails if lazy fields haven't been materialized yet.

   **Future escape hatch**: If profiling shows memory pressure for very large documents (hundreds of high-resolution images), a future version could add `load(..., lazy=True)` that defers image/table binary loading until `.data` / `.html` is first accessed, backed by the in-memory ZIP bytes. This would be opt-in and clearly documented as carrying the caveats above.

---

## 8. Retry & Polling Strategy

### HTTP Retry (transient errors)

```
Retryable: 409 (ABORTED), 429 (with retry_after), 503, 504, connection errors
NOT retryable: 429 without retry_after (quota exceeded), all other 4xx

Backoff: min(0.5 * 2^attempt + jitter, 30s)
         OR Retry-After header / details.retry_after value
Max retries: 5 (configurable, = 5 total attempts)
```

### Job Polling (adaptive)

```
Initial interval: poll_interval (default 10s)
After 60s elapsed: interval *= 1.2 per poll, capped at 30s
Terminal states: "done", "failed"
Timeout: poll_timeout (default 1800s / 30 min) → raises PollingTimeoutError
```

---

## 9. Configuration

### Timeout Scopes

The SDK has three distinct timeout scopes with different defaults, because the operations have very different latency profiles:

| Timeout | Scope | Default | Set On | What It Controls |
|---------|-------|---------|--------|-----------------|
| `timeout` | HTTP request | 60s | Constructor | Per-request timeout for API calls (`create`, `get`). Covers connect + read. |
| `upload_timeout` | HTTP request | 600s (10min) | Constructor | Per-request timeout for file upload PUT. Large files over slow connections need more time. |
| `poll_timeout` | Polling loop | 1800s (30min) | `parse()`, `wait()` | Wall-clock limit for the entire polling loop. This is NOT an HTTP timeout — it's how long to keep polling before giving up. |

**Why separate**: A user setting `timeout=30` intends fast-fail on API calls — they do NOT want the polling loop to die after 30 seconds. Conversely, `poll_timeout=120` limits how long to wait for processing, without affecting individual HTTP request timeouts.

```python
# Example: tight HTTP timeouts, generous polling
client = knowhere.Knowhere(
    api_key="sk_...",
    timeout=10.0,              # API calls fail fast (10s)
    upload_timeout=300.0,      # Upload allows 5 minutes
)

result = client.parse(
    file=Path("large_report.pdf"),
    poll_timeout=3600.0,       # Wait up to 1 hour for processing
)
```

### Priority Order (highest → lowest)

1. Per-call overrides (`poll_timeout=`, `poll_interval=`)
2. Constructor arguments (`api_key=`, `base_url=`, `timeout=`, `upload_timeout=`)
3. Environment variables (`KNOWHERE_API_KEY`, `KNOWHERE_BASE_URL`)
4. Defaults (`timeout=60.0`, `upload_timeout=600.0`, `poll_timeout=1800.0`, `max_retries=5`)

### Environment Variables

| Variable | Maps To | Default |
|----------|---------|---------|
| `KNOWHERE_API_KEY` | `api_key` | (required — error if missing) |
| `KNOWHERE_BASE_URL` | `base_url` | `https://api.knowhereto.ai` |
| `KNOWHERE_LOG_LEVEL` | log level | `WARNING` |

---

## 10. Logging

- Logger name: `"knowhere"`
- Level controlled by `KNOWHERE_LOG_LEVEL` env var
- **DEBUG**: Full request/response (URL, method, headers, body, status, response body)
- **INFO**: Request summary (method, path, status, duration)
- **WARNING**: Retries, rate limit hits
- **ERROR**: Final failures after retries exhausted
- **Sensitive header filtering**: `Authorization` header value → `"Bearer sk_...REDACTED"` in all log output

---

## 11. Version Compatibility & Requirements

### Python Version Support

| Python Version | Support Level | Notes |
|---------------|--------------|-------|
| 3.9 | Supported | Minimum version. Requires `typing-extensions` for backports. |
| 3.10 | Supported | |
| 3.11 | Supported | |
| 3.12 | Supported | |
| 3.13 | Supported | Latest stable |
| < 3.9 | NOT supported | Pydantic v2 requires 3.9+. |

### SDK Versioning Strategy

Follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.x → 2.x): Breaking changes to public API
- **MINOR** (1.1 → 1.2): New features, new methods, new optional parameters — backward compatible
- **PATCH** (1.1.0 → 1.1.1): Bug fixes, internal changes — no API changes

**Initial release**: `0.1.0` (pre-1.0 signals API may still evolve)

### API Version Compatibility

The SDK targets **Knowhere API v1** (`/v1/` endpoints). The API version is hardcoded in the client. When a v2 API is introduced, a new major SDK version will be released.

### Installation

```bash
# For SDK users
pip install knowhere-sdk
# or
uv add knowhere-sdk

# For SDK developers
cd packages/sdk-python
uv sync
```

### Dependencies

| Dependency | Constraint | Rationale |
|-----------|-----------|-----------|
| `httpx` | `>=0.25.0,<1.0` | Sync + async from one library; used by OpenAI/Anthropic SDKs |
| `pydantic` | `>=2.0.0,<3.0` | Response models; matches server's Pydantic v2 |
| `typing-extensions` | `>=4.7.0` | Python 3.9 compat for `TypedDict`, `Self`, etc. |

**No system-level dependencies**: Pure Python — no C compiler, no native libraries needed.

---

## 12. Dependencies & Package Management

### Package Manager: uv

We use **[uv](https://docs.astral.sh/uv/)** for development. SDK users install with whatever they prefer (`pip`, `uv`, `poetry`, etc.) — standard `pyproject.toml` is compatible with all PEP 517 tools.

### Developer Workflow

```bash
cd packages/sdk-python

uv sync                         # Create venv + install all deps
uv run pytest tests/ -v         # Run tests
uv run ruff check src/          # Lint
uv run mypy src/knowhere/       # Type check
uv build                        # Build sdist + wheel
```

### pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "knowhere-sdk"
version = "0.1.0"
description = "Official Python SDK for the Knowhere document parsing API"
readme = "README.md"
license = "MIT"
requires-python = ">=3.9"
authors = [
    { name = "Knowhere Team", email = "team@knowhereto.ai" },
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
]
dependencies = [
    "httpx>=0.25.0,<1.0",
    "pydantic>=2.0.0,<3.0",
    "typing-extensions>=4.7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.23.0",
    "respx>=0.21.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    "coverage>=7.0.0",
]

[project.urls]
Homepage = "https://knowhereto.ai"
Documentation = "https://docs.knowhereto.ai"
Repository = "https://github.com/Ontos-AI/knowhere-api"

[tool.hatch.build.targets.wheel]
packages = ["src/knowhere"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py39"
line-length = 100

[tool.mypy]
python_version = "3.9"
strict = true
```

### Build Backend: hatchling

Lightweight, modern build backend (~3 dependencies). Natively supports `src/` layout, requires minimal config, and is used by the OpenAI and Cloudflare Python SDKs. `uv build` calls hatchling under the hood.

---

## 13. Publishing & Release Workflow

### Branch Model

| Branch | Purpose | SDK Version | Publishes To |
|--------|---------|-------------|--------------|
| `staging` | Development & QA | Pre-release: `0.1.0rc1`, `0.1.0rc2`, ... | **TestPyPI** |
| `main` | Production release | Stable: `0.1.0`, `0.2.0`, `1.0.0` | **PyPI** |

### Version Lifecycle

```
feature branch → staging (rc on TestPyPI) → main (stable on PyPI)

Example:
  staging:  0.2.0rc1 → 0.2.0rc2 → 0.2.0rc3   (iterate on TestPyPI)
  main:     0.2.0                                (promote to PyPI)
```

### GitHub Actions Workflow

`.github/workflows/publish-sdk-python.yml`:

```yaml
name: Publish Python SDK

on:
  push:
    branches: [main, staging]
    paths:
      - 'packages/sdk-python/**'
    tags:
      - 'sdk-python-v*'

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: cd packages/sdk-python && uv sync
      - name: Lint
        run: cd packages/sdk-python && uv run ruff check src/
      - name: Type check
        run: cd packages/sdk-python && uv run mypy src/knowhere/
      - name: Test
        run: cd packages/sdk-python && uv run pytest tests/ -v

  publish-testpypi:
    needs: test
    if: github.ref == 'refs/heads/staging'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - name: Build
        run: cd packages/sdk-python && uv build
      - name: Publish to TestPyPI
        run: cd packages/sdk-python && uv publish --index-url https://test.pypi.org/legacy/
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.TESTPYPI_API_TOKEN }}

  publish-pypi:
    needs: test
    if: startsWith(github.ref, 'refs/tags/sdk-python-v')
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - name: Build
        run: cd packages/sdk-python && uv build
      - name: Publish to PyPI
        run: cd packages/sdk-python && uv publish
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

### Release Checklist

**Staging (pre-release to TestPyPI):**
1. Bump version in `_version.py` to `X.Y.ZrcN`
2. Run `uv lock` to update lockfile
3. Push to `staging` branch
4. CI runs tests across Python 3.9–3.13
5. CI publishes to TestPyPI automatically

**Production (stable release to PyPI):**
1. Merge `staging` → `main`
2. Bump version in `_version.py` to `X.Y.Z` (remove `rcN`)
3. Create git tag: `git tag sdk-python-vX.Y.Z`
4. Push tag: `git push origin sdk-python-vX.Y.Z`
5. CI publishes to PyPI automatically

### Required Secrets

| Secret | Purpose |
|--------|---------|
| `TESTPYPI_API_TOKEN` | Publish to TestPyPI (staging) |
| `PYPI_API_TOKEN` | Publish to PyPI (production) |

---

## 14. Testing Strategy

### Unit Tests (mocked HTTP via `respx`)

| Test File | Covers |
|-----------|--------|
| `test_client.py` | Constructor, env var resolution, missing API key error, context manager |
| `test_exceptions.py` | Status→exception mapping, error body parsing, retry_after extraction |
| `test_models.py` | Pydantic serialize/deserialize, `is_terminal`/`is_done`/`is_failed` |
| `test_jobs.py` | Jobs resource: create, get, upload, wait, load |
| `test_parse.py` | High-level `parse()` method (URL + file flows) |
| `test_polling.py` | Adaptive interval, timeout → `PollingTimeoutError`, multi-status sequence |
| `test_upload.py` | File streaming (bytes/Path/BinaryIO), presigned URL upload |
| `test_result_parser.py` | ZIP parsing, manifest/chunks deserialization, image/table loading, checksum verification |
| `test_retry.py` | 429 with retry_after → retry; 429 without → no retry; 503/504 → retry |
| `test_logging.py` | Sensitive header redaction |

### Integration Tests (gated by env var)

```python
@pytest.mark.skipif(not os.environ.get("KNOWHERE_API_KEY"), reason="No API key")
def test_parse_e2e():
    client = knowhere.Knowhere()
    result = client.parse(url="https://example.com/test.pdf", poll_timeout=120)
    assert len(result.chunks) > 0
    assert result.manifest.statistics.total_chunks > 0
```

---

## 15. Implementation Sequence

### Phase 1: Foundation (no HTTP calls)
1. `_version.py`, `_constants.py` — version string, default URL, env var names
2. `_types.py` — `NotGiven` sentinel, type aliases
3. `_exceptions.py` — full exception hierarchy (including `JobFailedError`, `ChecksumError`)
4. `types/result.py` — `ParseResult`, `Manifest`, all `Chunk` types, `Statistics`, etc.
5. `types/job.py` — `Job`, `JobResult`, `JobError`
6. `types/params.py` — `ParsingParams`, `WebhookConfig` TypedDicts

### Phase 2: Core Client
7. `_logging.py` — logger setup, header filtering
8. `_response.py` — `APIResponse` wrapper
9. `_base_client.py` — config resolution, auth headers, retry logic, error parsing
10. `_client.py` — `Knowhere` + `AsyncKnowhere` with `parse()` method

### Phase 3: Jobs Resource & Helpers
11. `resources/_base.py` — `SyncAPIResource` / `AsyncAPIResource`
12. `resources/jobs.py` — all Jobs methods (create, get, upload, wait, load)
13. `lib/upload.py` — presigned URL streaming upload (sync + async)
14. `lib/polling.py` — adaptive polling loop (sync + async)
15. `lib/result_parser.py` — ZIP loading, checksum verification, `ParseResult` construction

### Phase 4: Public Surface & Package
16. `resources/__init__.py`, `types/__init__.py` — re-exports
17. `__init__.py` — public API surface
18. `pyproject.toml`, `py.typed` — package config

### Phase 5: Tests & Examples
19. `tests/conftest.py` + all test files
20. `examples/` — usage examples

---

## 16. Critical Source Files Referenced

| Purpose | File |
|---------|------|
| Job schemas (source of truth) | `packages/shared-python/shared/models/schemas/job.py` |
| Error codes & retry semantics | `packages/shared-python/shared/core/response/ErrorCode.py` |
| Exception hierarchy | `packages/shared-python/shared/core/exceptions/domain_exceptions.py` |
| API routes | `apps/api/app/api/v1/routes/jobs.py` |
| Error response format | `apps/api/app/core/exception_handlers.py` |
| Authentication | `apps/api/app/core/dependencies.py` |
| Result ZIP format | `docs/result.md` |

These are read-only references. The SDK does NOT import from or depend on any of these packages.

---

## 17. Verification Plan

1. **Unit tests**: `uv run pytest tests/` — all mocked, no network
2. **Type checking**: `uv run mypy src/knowhere/`
3. **Linting**: `uv run ruff check src/`
4. **Integration test** (manual): Set `KNOWHERE_API_KEY` and run `uv run pytest tests/ -k integration -v`
5. **Example scripts**: Run `uv run python examples/parse_url.py` against staging API
