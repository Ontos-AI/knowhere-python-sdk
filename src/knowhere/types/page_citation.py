"""Typed page-citation asset descriptors stored on chunk metadata."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

PAGE_CITATION_ASSETS_METADATA_KEY = "pageAssets"

PageCitationAssetContentType = Literal["image/png", "image/jpeg"]
PageCitationAssetSource = Literal["knowhere-rendered-page-citation-source"]


class PageCitationAsset(BaseModel):
    """Server-provided page citation asset descriptor.

    Stored on chunk metadata under ``pageAssets``. The SDK does not generate
    these assets; it only types descriptors returned by Knowhere.
    """

    page_num: int
    artifact_ref: str
    asset_url: Optional[str] = None
    content_type: PageCitationAssetContentType
    width: Optional[int] = None
    height: Optional[int] = None
    source: PageCitationAssetSource
