# Knowhere Python SDK

[![PyPI version](https://img.shields.io/pypi/v/knowhere-python-sdk.svg)](https://pypi.org/project/knowhere-python-sdk/)

Official Python SDK for the [Knowhere](https://knowhereto.ai) document parsing API.

## Installation

```sh
pip install knowhere-python-sdk
```

Or with [uv](https://docs.astral.sh/uv/):

```sh
uv add knowhere-python-sdk
```

## Usage

```python
import knowhere

client = knowhere.Knowhere(api_key="sk_...")

result = client.parse(url="https://example.com/report.pdf")

print(result.statistics.total_chunks)
print(result.full_markdown[:200])

for chunk in result.text_chunks:
    print(chunk.content[:80])
```

## Retrieval and document lifecycle

New documents are published into a retrieval namespace. The server returns a
stable `document_id` after the job is published. `client.jobs.create(...)`
does not return a usable `document_id`; persist `job_result.document_id` if you
need to update or archive the same document later.

```python
job = client.jobs.create(
    source_type="url",
    source_url="https://example.com/manual.pdf",
    namespace="support-center",
)

job_result = client.jobs.wait(job.job_id)
document_id = job_result.document_id

if document_id is None:
    raise RuntimeError("Expected document_id after successful publication.")
```

After the job is done and published, query the canonical document content:

```python
response = client.retrieval.query(
    namespace="support-center",
    query="How do I reset Bluetooth pairing?",
    top_k=5,
    channels=["path", "term"],
    filter_mode="keep",
    signal_paths=["Bluetooth", "Pairing"],
)

print(response.router_used)

for result in response.results:
    print(result.content)
    print(result.score)
    print(result.source.source_file_name, result.source.section_path)
```

Use `document_id` to update or archive a document:

```python
update_job = client.jobs.create(
    source_type="url",
    source_url="https://example.com/manual-v2.pdf",
    document_id=document_id,
)

document = client.documents.get(document_id)
print(document.status)

client.documents.archive(document_id)
```

You can also list documents in a namespace:

```python
documents = client.documents.list(namespace="support-center")
for document in documents.documents:
    print(document.document_id, document.status)
```

Retrieval supports exclusions when clients want follow-up results that avoid
previously used documents or sections:

```python
response = client.retrieval.query(
    namespace="support-center",
    query="battery charging",
    exclude_document_ids=["doc_old"],
    exclude_sections=[
        {"document_id": "doc_123", "section_path": "Appendix / Legal"}
    ],
)
```

While you can provide an `api_key` keyword argument, we recommend using [python-dotenv](https://pypi.org/project/python-dotenv/) to add `KNOWHERE_API_KEY="sk_..."` to your `.env` file so that your API key is not stored in source control.

### Parse a local file

```python
from pathlib import Path

result = client.parse(
    file=Path("report.pdf"),
    parsing_params={"model": "advanced", "ocr_enabled": True},
)

print(result.manifest.source_file_name)  # "report.pdf"
print(len(result.chunks))                # 152
print(result.namespace)                  # "default" or your explicit namespace
print(result.document_id)                # Published canonical document id
```

### Access different chunk types

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

### Save all results to disk

```python
result = client.parse(file=Path("report.pdf"))
result.save("./output/report/")
```

## Async usage

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

## Step-by-step control

For granular control over the parsing workflow, use the `jobs` resource directly:

```python
from pathlib import Path

# Step 1: Create a parsing job
job = client.jobs.create(
    source_type="file",
    file_name="report.pdf",
    namespace="support-center",
    parsing_params={"model": "advanced", "ocr_enabled": True},
)

# Step 2: Upload file to presigned URL
client.jobs.upload(job, file=Path("report.pdf"))

# Step 3: Poll until done (adaptive backoff)
job_result = client.jobs.wait(job.job_id, poll_interval=10.0, poll_timeout=1800.0)

print(job_result.document_id)  # Persist this to update/archive the document later.

# Step 4: Download and parse results
result = client.jobs.load(job_result)
print(result.statistics)
```

## Handling errors

All errors inherit from `knowhere.KnowhereError`.


```python
import knowhere

try:
    result = client.parse(url="https://example.com/report.pdf")
except knowhere.AuthenticationError:
    print("Invalid API key")
except knowhere.APIStatusError as e:
    print(f"{e.status_code}: {e.message}")
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

### Retries

Connection errors, 429 Rate Limit, and >=500 Internal errors are automatically retried with exponential backoff.

```python
client = knowhere.Knowhere(
    api_key="sk_...",
    max_retries=3,  # default is 5
)
```

### Determining the installed version

```python
import knowhere
print(knowhere.__version__)
```

## Versioning

This package follows [Semantic Versioning](https://semver.org/).

We publish stable releases to [PyPI](https://pypi.org/project/knowhere-python-sdk/). To install the latest unreleased changes directly from the repository: https://github.com/Ontos-AI/knowhere-python-sdk

## Requirements

- Python 3.9+
- [httpx](https://www.python-httpx.org/) `>=0.25.0,<1.0`
- [pydantic](https://docs.pydantic.dev/) `>=2.0.0,<3.0`
- [typing-extensions](https://pypi.org/project/typing-extensions/) `>=4.7.0`

## Community

- Contributing guide: [CONTRIBUTING.md](./CONTRIBUTING.md)
- Security policy: [SECURITY.md](./SECURITY.md)
- Code of conduct: [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)

## License

MIT
