from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageCandidate:
    url: str
    source_page: str
    discovered_by: str
    alt: str | None = None


@dataclass(frozen=True)
class ImagePermission:
    source_id: str
    source_page: str
    asset_url_prefix: str
    reuse_basis: str
    evidence_url: str
