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


class LLMModelsConfig(TypedDict, total=False):
    """Per-channel model ids sharing root api_key / base_url."""

    text: str
    vision: str


class LLMConfig(TypedDict, total=False):
    """Bring-your-own-key LLM credentials.

    Flat root (``api_key`` / ``model`` / ``base_url``) applies to both channels.
    Use ``models`` for different model ids on the same endpoint, or ``text`` /
    ``vision`` objects for different provider endpoints.
    """

    api_key: str
    model: str
    base_url: str
    models: LLMModelsConfig
    text: LLMProviderConfig
    vision: LLMProviderConfig


class WebhookConfig(TypedDict, total=False):
    """Webhook configuration for job completion notifications."""

    url: str
