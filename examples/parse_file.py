"""Parse a local PDF file with the advanced model and OCR enabled.

Demonstrates parsing a local file, accessing different chunk types
(text, image, table), saving extracted images, and persisting all
results to disk.

Prerequisites:
    export KNOWHERE_API_KEY="sk_..."
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from knowhere import Knowhere
from knowhere.types import (
    ImageChunk,
    ParseResult,
    TableChunk,
    TextChunk,
)


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

    print(f"Parsing local file: {file_path.resolve()}")
    result: ParseResult = client.parse(
        file=file_path,
        model="advanced",
        ocr=True,
    )

    print(f"Job ID: {result.job_id}")

    # -- Text chunks ---------------------------------------------------------
    text_chunks: list[TextChunk] = result.text_chunks
    print(f"\nText chunks ({len(text_chunks)}):")
    for chunk in text_chunks[:3]:
        preview: str = chunk.content[:100].replace("\n", " ")
        print(f"  [{chunk.chunk_id}] {preview}...")

    # -- Image chunks --------------------------------------------------------
    image_chunks: list[ImageChunk] = result.image_chunks
    print(f"\nImage chunks ({len(image_chunks)}):")
    for chunk in image_chunks[:3]:
        print(f"  [{chunk.chunk_id}] {chunk.content[:80]}...")

    # -- Table chunks --------------------------------------------------------
    table_chunks: list[TableChunk] = result.table_chunks
    print(f"\nTable chunks ({len(table_chunks)}):")
    for chunk in table_chunks[:3]:
        preview: str = chunk.content[:100].replace("\n", " ")
        print(f"  [{chunk.chunk_id}] {preview}...")

    # -- Save all results to disk --------------------------------------------
    output_directory: Path = Path("output")
    result.save(output_directory)
    print(f"\nAll results saved to: {output_directory.resolve()}")

    # -- Access the document hierarchy ---------------------------------------
    hierarchy: dict = result.hierarchy  # type: ignore[type-arg]
    print(f"Document hierarchy keys: {list(hierarchy.keys())}")


if __name__ == "__main__":
    main()
