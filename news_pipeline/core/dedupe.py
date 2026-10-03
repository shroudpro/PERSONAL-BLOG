from __future__ import annotations

from typing import Any

from news_pipeline.core.models import NewsItem
from news_pipeline.core.normalize import normalize_title, normalize_url


class DedupeIndex:
    def __init__(self) -> None:
        self._urls: set[str] = set()
        self._titles: set[str] = set()
        self._content_hashes: set[str] = set()
        self._ids: set[str] = set()
        self._records: dict[str, dict[str, Any]] = {}

    def duplicate_reason(self, item: NewsItem) -> str | None:
        canonical = normalize_url(item.canonical_url)
        if canonical in self._urls:
            return "canonical_url"
        title = normalize_title(item.title)
        if title and title in self._titles:
            return "normalized_title"
        if item.content_hash and item.content_hash in self._content_hashes:
            return "content_hash"
        if item.id in self._ids:
            return "id"
        return None

    def add(self, item: NewsItem) -> bool:
        if self.duplicate_reason(item):
            return False
        self.add_record(
            {
                "id": item.id,
                "canonical_url": item.canonical_url,
                "normalized_title": normalize_title(item.title),
                "content_hash": item.content_hash,
            }
        )
        return True

    def add_record(self, record: dict[str, Any]) -> bool:
        item_id = str(record.get("id", ""))
        canonical_value = record.get("canonical_url")
        canonical = normalize_url(canonical_value) if isinstance(canonical_value, str) and canonical_value else ""
        title_value = record.get("normalized_title") or record.get("title") or ""
        normalized_title = normalize_title(str(title_value))
        content_hash = record.get("content_hash")

        if canonical and canonical in self._urls:
            return False
        if normalized_title and normalized_title in self._titles:
            return False
        if isinstance(content_hash, str) and content_hash and content_hash in self._content_hashes:
            return False
        if item_id and item_id in self._ids:
            return False

        if canonical:
            self._urls.add(canonical)
        if normalized_title:
            self._titles.add(normalized_title)
        if isinstance(content_hash, str) and content_hash:
            self._content_hashes.add(content_hash)
        if item_id:
            self._ids.add(item_id)
            self._records[item_id] = {
                "id": item_id,
                "canonical_url": canonical,
                "normalized_title": normalized_title,
                "content_hash": content_hash if isinstance(content_hash, str) else None,
            }
        return True

    @property
    def records(self) -> list[dict[str, Any]]:
        return [self._records[item_id] for item_id in sorted(self._records)]
