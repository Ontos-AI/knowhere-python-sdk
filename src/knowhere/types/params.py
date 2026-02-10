"""TypedDicts for request parameters."""

from __future__ import annotations


from typing_extensions import TypedDict


class ParsingParams(TypedDict, total=False):
    """Optional parsing parameters for job creation."""

    model: str
    ocr_enabled: bool
    kb_dir: str
    doc_type: str
    smart_title_parse: bool
    summary_image: bool
    summary_table: bool
    summary_txt: bool
    add_frag_desc: bool


class WebhookConfig(TypedDict, total=False):
    """Webhook configuration for job completion notifications."""

    url: str
