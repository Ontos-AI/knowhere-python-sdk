"""Parse a document from a public URL.

Demonstrates the simplest usage of the Knowhere SDK: parse a document
by URL, inspect statistics, and iterate over text chunks.

Prerequisites:
    export KNOWHERE_API_KEY="sk_..."
"""

from __future__ import annotations

import os
import sys

from knowhere import Knowhere
from knowhere.types import ParseResult, TextChunk, Statistics


def main() -> None:
    api_key: str | None = os.environ.get("KNOWHERE_API_KEY")
    if not api_key:
        print("Error: KNOWHERE_API_KEY environment variable is not set.")
        sys.exit(1)

    client: Knowhere = Knowhere(api_key=api_key)

    document_url: str = "https://arxiv.org/pdf/1706.03762"
    print(f"Parsing document from URL: {document_url}")

    result: ParseResult = client.parse(url=document_url)

    # -- Statistics ----------------------------------------------------------
    statistics: Statistics = result.statistics
    print(f"\nJob ID:       {result.job_id}")
    print(f"Total chunks: {statistics.total_chunks}")
    print(f"Text chunks:  {statistics.text_chunks}")
    print(f"Image chunks: {statistics.image_chunks}")
    print(f"Table chunks: {statistics.table_chunks}")

    # -- Iterate text chunks -------------------------------------------------
    text_chunks: list[TextChunk] = result.text_chunks
    print(f"\n--- First 5 text chunks (of {len(text_chunks)}) ---")
    for chunk in text_chunks[:5]:
        preview: str = chunk.content[:120].replace("\n", " ")
        print(f"  [{chunk.chunk_id}] {preview}...")

    # -- Full markdown -------------------------------------------------------
    full_markdown: str = result.full_markdown
    print(f"\nFull markdown length: {len(full_markdown)} characters")


if __name__ == "__main__":
    main()
