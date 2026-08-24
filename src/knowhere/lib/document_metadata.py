"""Official-client document metadata defaults for job creates."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from knowhere._version import __version__

# Wire format: ``{ created_by_client, client_version }``.
PYTHON_SDK_DOCUMENT_METADATA_DEFAULTS: Dict[str, Any] = {
    "created_by_client": "python-sdk",
    "client_version": __version__,
}


def merge_document_metadata_defaults(
    defaults: Mapping[str, Any],
    provided: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge official-client defaults under caller-provided metadata.

    Caller keys win; defaults fill keys that are missing.
    """
    merged: Dict[str, Any] = dict(defaults)
    if provided:
        merged.update(dict(provided))
    return merged
