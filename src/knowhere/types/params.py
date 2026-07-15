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


class LLMProviderConfig(TypedDict, total=False):
    """OpenAI-compatible provider credentials for a single modality."""

    api_key: str
    model: str
    base_url: str


class LLMConfig(TypedDict, total=False):
    """Bring-your-own-key LLM credentials.

    At least one of ``text`` or ``vision`` should be set when ``llm_config``
    is present. Providers must be OpenAI-compatible.
    """

    text: LLMProviderConfig
    vision: LLMProviderConfig


class WebhookConfig(TypedDict, total=False):
    """Webhook configuration for job completion notifications."""

    url: str
