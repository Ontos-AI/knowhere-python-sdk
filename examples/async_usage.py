"""Async usage with AsyncKnowhere.

Demonstrates how to use the async client with ``async with`` context
management to parse documents concurrently.

Prerequisites:
    export KNOWHERE_API_KEY="sk_..."
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from knowhere import AsyncKnowhere
from knowhere.types import ParseResult


async def parseFromUrl(client: AsyncKnowhere) -> ParseResult:
    """Parse a remote document by URL."""
    document_url: str = "https://arxiv.org/pdf/1706.03762"
    print(f"[URL]  Parsing: {document_url}")
    result: ParseResult = await client.parse(url=document_url)
    print(f"[URL]  Done -- {result.statistics.total_chunks} chunks")
    return result


async def parseFromFile(client: AsyncKnowhere) -> ParseResult:
    """Parse a local PDF file."""
    file_path: Path = Path("report.pdf")
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path.resolve()}")

    print(f"[FILE] Parsing: {file_path.resolve()}")
    result: ParseResult = await client.parse(
        file=file_path,
        model="advanced",
        ocr=True,
    )
    print(f"[FILE] Done -- {result.statistics.total_chunks} chunks")
    return result


async def main() -> None:
    api_key: str | None = os.environ.get("KNOWHERE_API_KEY")
    if not api_key:
        print("Error: KNOWHERE_API_KEY environment variable is not set.")
        sys.exit(1)

    async with AsyncKnowhere(api_key=api_key) as client:
        # Run both parse operations concurrently
        url_result, file_result = await asyncio.gather(
            parseFromUrl(client),
            parseFromFile(client),
        )

        print("\n--- URL result ---")
        print(f"  Job ID:       {url_result.job_id}")
        print(f"  Text chunks:  {len(url_result.text_chunks)}")
        print(f"  Markdown len: {len(url_result.full_markdown)}")

        print("\n--- File result ---")
        print(f"  Job ID:       {file_result.job_id}")
        print(f"  Text chunks:  {len(file_result.text_chunks)}")
        print(f"  Image chunks: {len(file_result.image_chunks)}")
        print(f"  Table chunks: {len(file_result.table_chunks)}")


if __name__ == "__main__":
    asyncio.run(main())
