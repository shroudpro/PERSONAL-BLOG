from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from news_pipeline.core.normalize import clean_text, is_domain_allowed, normalize_datetime, normalize_title, normalize_url


SourceType = Literal["official", "research"]
FetchMethod = Literal["feed", "api", "sitemap", "html", "arxiv"]


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    source_type: SourceType
    homepage: str
    enabled: bool
    priority: int
    fetch_method: FetchMethod
    allowed_domains: tuple[str, ...]
    default_tags: tuple[str, ...] = ()
    notes: str = ""
    language: str | None = None
    feed_url: str | None = None
    feed_urls: tuple[str, ...] = ()
    api_url: str | None = None
    api_items_path: str | None = None
    api_field_map: Mapping[str, str] = field(default_factory=dict)
    sitemap_urls: tuple[str, ...] = ()
    list_url: str | None = None
    item_url_patterns: tuple[str, ...] = ()
    exclude_url_patterns: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()

    @property
    def endpoints(self) -> tuple[str, ...]:
        values = list(self.feed_urls or ((self.feed_url,) if self.feed_url else ()))
        values.extend(self.sitemap_urls)
        for endpoint in (self.api_url, self.list_url):
            if endpoint:
                values.append(endpoint)
        return tuple(values)


@dataclass(frozen=True)
class NewsItem:
    id: str
    source_id: str
    source_name: str
    source_type: SourceType
    title: str
    url: str
    canonical_url: str
    published_at: str | None
    fetched_at: str
    author: str | None = None
    language: str | None = None
    summary_raw: str | None = None
    content_text: str | None = None
    tags_raw: list[str] = field(default_factory=list)
    category_raw: str | None = None
    image_url: str | None = None
    image_alt: str | None = None
    image_source: str | None = None
    content_hash: str | None = None
    status: str = "collected"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_news_item(
    *,
    source: SourceConfig,
    url: str,
    title: str,
    fetched_at: datetime | str,
    published_at: datetime | str | None = None,
    canonical_url: str | None = None,
    author: str | None = None,
    language: str | None = None,
    summary_raw: str | None = None,
    content_text: str | None = None,
    tags: tuple[str, ...] | list[str] = (),
    category_raw: str | None = None,
    image_url: str | None = None,
    image_alt: str | None = None,
    image_source: str | None = None,
) -> NewsItem:
    normalized_url = normalize_url(url)
    candidate_canonical = normalize_url(canonical_url or normalized_url)
    normalized_canonical = (
        candidate_canonical
        if is_domain_allowed(candidate_canonical, source.allowed_domains)
        else normalized_url
    )
    cleaned_title = clean_text(title)
    if not cleaned_title:
        raise ValueError("News item title cannot be empty")

    cleaned_summary = clean_text(summary_raw)
    cleaned_content = clean_text(content_text)
    hash_content = normalize_title(cleaned_content or cleaned_summary or "")
    content_hash = hashlib.sha256(hash_content.encode("utf-8")).hexdigest() if hash_content else None
    item_id = hashlib.sha256(normalized_canonical.encode("utf-8")).hexdigest()[:16]
    combined_tags = list(dict.fromkeys(tag.strip() for tag in (*source.default_tags, *tags) if tag.strip()))
    fetched_value = normalize_datetime(fetched_at)
    if fetched_value is None:
        raise ValueError("fetched_at must be a valid timestamp")

    return NewsItem(
        id=item_id,
        source_id=source.id,
        source_name=source.name,
        source_type=source.source_type,
        title=cleaned_title,
        url=url,
        canonical_url=normalized_canonical,
        published_at=normalize_datetime(published_at),
        fetched_at=fetched_value,
        author=clean_text(author),
        language=language or source.language,
        summary_raw=cleaned_summary,
        content_text=cleaned_content,
        tags_raw=combined_tags,
        category_raw=clean_text(category_raw),
        image_url=image_url,
        image_alt=clean_text(image_alt),
        image_source=image_source or (source.homepage if image_url else None),
        content_hash=content_hash,
    )
