"""Versioned starter profiles for public listing sources.

Selectors are deliberately shipped with ``terms_checked=false``. They reduce
manual setup, while the operator still has to verify the current terms and
robots.txt before the API allows a crawl to run.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .config import settings


class SourceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["scrapy", "playwright", "manual"]
    connector_type: Literal["first_party", "partner_feed", "rest_api", "html_static", "html_playwright", "official_notice", "community_api"]
    integration_status: Literal["ready", "legal_review", "partner_required"]
    start_url: str = ""


PROFILES = TypeAdapter(list[SourceProfile])

PROFILE_CONFIG_OVERRIDES: dict[str, dict] = {}


def _starter_config(profile: SourceProfile) -> dict:
    if profile.connector_type == "first_party":
        return {"item_selector": "__first_party__", "terms_checked": True}
    if profile.connector_type in {"partner_feed", "rest_api", "community_api"}:
        return {"item_selector": "__official_api_only__", "terms_checked": False}
    config = {
        "item_selector": "article, .property-item, .post-item, .room-item",
        "link_selector": "a::attr(href)",
        "text_selector": "article ::text, main ::text",
        "image_selector": "article img::attr(src), main img::attr(src)",
        "next_selector": "a[rel='next']::attr(href), .pagination a::attr(href)",
        "terms_checked": False,
    }
    config.update(PROFILE_CONFIG_OVERRIDES.get(profile.id, {}))
    return config


@lru_cache(maxsize=1)
def profiles() -> list[dict]:
    path = Path(settings.crawler_dir) / "source_profiles.json"
    if not path.is_file():
        return []
    parsed = PROFILES.validate_python(json.loads(path.read_text(encoding="utf-8")))
    ids = [profile.id for profile in parsed]
    if len(ids) != len(set(ids)):
        raise ValueError("Source profile ids must be unique")
    return [{**profile.model_dump(), "config": _starter_config(profile)} for profile in parsed]
