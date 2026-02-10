# Knowhere Python SDK

Official Python SDK for the [Knowhere](https://knowhereto.ai) document parsing API.

## Installation

```bash
pip install knowhere-python-sdk
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add knowhere-python-sdk
```

## Quick Start

```python
import knowhere

client = knowhere.Knowhere(api_key="sk_...")

# Parse a document from URL
result = client.parse(url="https://example.com/report.pdf")

print(result.statistics.total_chunks)  # 152
print(result.full_markdown[:200])      # First 200 chars of full markdown

for chunk in result.text_chunks:
    print(chunk.content[:80])
```

### Parse a Local File

```python
from pathlib import Path

result = client.parse(
    file=Path("report.pdf"),
    parsing_params={"model": "advanced", "ocr_enabled": True},
)

print(result.manifest.source_file_name)  # "report.pdf"
print(len(result.chunks))                # 152
```

### Access Different Chunk Types

```python
result = client.parse(url="https://example.com/report.pdf")

# Text chunks
for chunk in result.text_chunks:
    print(chunk.keywords)
    print(chunk.summary)

# Image chunks (raw bytes loaded from ZIP)
for chunk in result.image_chunks:
    print(chunk.file_path)
    print(len(chunk.data))       # bytes
    chunk.save("./output/")      # writes image to disk

# Table chunks (HTML loaded from ZIP)
for chunk in result.table_chunks:
    print(chunk.file_path)
    print(chunk.html[:100])
```

### Save All Results to Disk

```python
result = client.parse(file=Path("report.pdf"))
result.save("./output/report/")
```

## Async Usage

```python
import asyncio
import knowhere

async def main():
    async with knowhere.AsyncKnowhere(api_key="sk_...") as client:
        result = await client.parse(url="https://example.com/report.pdf")
        print(result.statistics.total_chunks)

        for chunk in result.text_chunks:
            print(chunk.summary)

asyncio.run(main())
```

## Step-by-Step Control

For granular control over the parsing workflow, use the `jobs` resource directly:

```python
from pathlib import Path

# Step 1: Create a parsing job
job = client.jobs.create(
    source_type="file",
    file_name="report.pdf",
    parsing_params={"model": "advanced", "ocr_enabled": True},
)

# Step 2: Upload file to presigned URL
client.jobs.upload(job, file=Path("report.pdf"))

# Step 3: Poll until done (adaptive backoff)
job_result = client.jobs.wait(job.job_id, poll_interval=10.0, poll_timeout=1800.0)

# Step 4: Download and parse results
result = client.jobs.load(job_result)
print(result.statistics)
```

## Configuration

The SDK reads configuration from constructor arguments, environment variables, or defaults (in that priority order):

| Variable | Description | Default |
|----------|-------------|---------|
| `KNOWHERE_API_KEY` | API key (required) | — |
| `KNOWHERE_BASE_URL` | API base URL | `https://api.knowhereto.ai` |
| `KNOWHERE_LOG_LEVEL` | Log level | `WARNING` |

```python
# Uses environment variables automatically
client = knowhere.Knowhere()

# Or configure explicitly
client = knowhere.Knowhere(
    api_key="sk_...",
    base_url="https://api.knowhereto.ai",
    timeout=30.0,           # HTTP request timeout (default: 60s)
    upload_timeout=300.0,   # File upload timeout (default: 600s)
    max_retries=3,          # Max retry attempts (default: 5)
)
```

### Context Manager

```python
# Sync — ensures httpx.Client is properly closed
with knowhere.Knowhere(api_key="sk_...") as client:
    result = client.parse(url="https://example.com/report.pdf")

# Async — ensures httpx.AsyncClient is properly closed
async with knowhere.AsyncKnowhere(api_key="sk_...") as client:
    result = await client.parse(url="https://example.com/report.pdf")
```

## Error Handling

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
    print(e.retry_after)   # seconds to wait
except AuthenticationError:
    print("Invalid API key")
except PollingTimeoutError:
    print("Job did not complete within timeout")
except APIStatusError as e:
    print(f"API error {e.status_code}: {e.message}")
```

## Requirements

- Python 3.9+
- [httpx](https://www.python-httpx.org/) `>=0.25.0,<1.0`
- [pydantic](https://docs.pydantic.dev/) `>=2.0.0,<3.0`
- [typing-extensions](https://pypi.org/project/typing-extensions/) `>=4.7.0`

## Building from Source

### Prerequisites

- Python 3.9 or later
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Build

```bash
git clone https://github.com/Ontos-AI/knowhere-python-sdk.git
cd knowhere-python-sdk

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Build sdist + wheel
uv build

# Install the built wheel
pip install dist/knowhere_python_sdk-*.whl
```

## Development

### Setup

```bash
git clone https://github.com/Ontos-AI/knowhere-python-sdk.git
cd knowhere-python-sdk

# Create venv and install all dependencies (including dev)
uv sync --all-extras
```

### Running Tests

```bash
# Run all unit tests
uv run pytest tests/ -v

# Run with coverage
uv run coverage run -m pytest tests/ -v
uv run coverage report -m
```

### Linting and Type Checking

```bash
# Lint
uv run ruff check src/

# Type check
uv run mypy src/knowhere/
```

### Project Structure

```
knowhere-python-sdk/
├── src/knowhere/
│   ├── __init__.py              # Public API surface
│   ├── _client.py               # Knowhere + AsyncKnowhere clients
│   ├── _base_client.py          # HTTP logic, retry, error parsing
│   ├── _exceptions.py           # Exception hierarchy
│   ├── _constants.py            # Default URLs, timeouts, env var names
│   ├── _types.py                # Sentinel types, callback type aliases
│   ├── _logging.py              # Logger setup, header redaction
│   ├── _response.py             # APIResponse wrapper
│   ├── _version.py              # __version__
│   ├── py.typed                 # PEP 561 marker
│   ├── types/
│   │   ├── job.py               # Job, JobResult, JobError
│   │   ├── result.py            # ParseResult, Manifest, Chunk types
│   │   └── params.py            # ParsingParams, WebhookConfig
│   ├── resources/
│   │   └── jobs.py              # Jobs + AsyncJobs resource
│   └── lib/
│       ├── polling.py           # Adaptive polling loop
│       ├── upload.py            # Streaming file upload
│       └── result_parser.py     # ZIP parsing, checksum verification
├── tests/                       # Unit tests (respx-mocked HTTP)
├── examples/                    # Usage examples
└── pyproject.toml
```

## License

MIT
