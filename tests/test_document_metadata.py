"""Tests for official-client document metadata merge."""

from __future__ import annotations

from knowhere._version import __version__
from knowhere.lib.document_metadata import (
    PYTHON_SDK_DOCUMENT_METADATA_DEFAULTS,
    merge_document_metadata_defaults,
)


class TestMergeDocumentMetadataDefaults:
    def test_fills_defaults_when_metadata_omitted(self) -> None:
        assert merge_document_metadata_defaults(PYTHON_SDK_DOCUMENT_METADATA_DEFAULTS) == {
            "created_by_client": "python-sdk",
            "client_version": __version__,
        }

    def test_fills_only_missing_keys(self) -> None:
        assert merge_document_metadata_defaults(
            PYTHON_SDK_DOCUMENT_METADATA_DEFAULTS,
            {"title": "Report.pdf"},
        ) == {
            "created_by_client": "python-sdk",
            "client_version": __version__,
            "title": "Report.pdf",
        }

    def test_caller_keys_win(self) -> None:
        assert merge_document_metadata_defaults(
            PYTHON_SDK_DOCUMENT_METADATA_DEFAULTS,
            {
                "created_by_client": "cli",
                "client_version": "9.9.9",
                "title": "Report.pdf",
            },
        ) == {
            "created_by_client": "cli",
            "client_version": "9.9.9",
            "title": "Report.pdf",
        }
