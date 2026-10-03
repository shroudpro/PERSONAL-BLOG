from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from news_pipeline.collectors.base import BaseCollector
from news_pipeline.core.models import NewsItem, SourceConfig, build_news_item
from news_pipeline.core.normalize import is_domain_allowed, normalize_datetime, parse_datetime_value


def _value_at_path(value: Any, path: str) -> Any:
    current = value
    for component in path.split(".") if path else ():
        if isinstance(current, list):
            try:
                current = current[int(component)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(component)
        else:
            return None
    return current


def parse_api_response(
    payload: Any,
    source: SourceConfig,
    fetched_at: datetime,
    *,
    since_hours: int,
    limit: int | None = None,
) -> list[NewsItem]:
    if not source.api_items_path or not source.api_field_map:
        raise ValueError(f"API item path and field map are required for {source.id}")
    records = _value_at_path(payload, source.api_items_path)
    if not isinstance(records, list):
        raise ValueError(f"API item path did not resolve to a list for {source.id}")

    cutoff = fetched_at.astimezone(timezone.utc) - timedelta(hours=since_hours)
    items: list[NewsItem] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        field = lambda name: (
            _value_at_path(record, source.api_field_map[name]) if name in source.api_field_map else None
        )
        title = field("title")
        url = field("url")
        if not isinstance(title, str) or not title.strip() or not isinstance(url, str):
            continue
        if not is_domain_allowed(url, source.allowed_domains):
            continue

        published_value = field("published_at")
        published = parse_datetime_value(published_value) if published_value else None
        if published and published < cutoff:
            continue
        tags_value = field("tags")
        if isinstance(tags_value, str):
            tags = (tags_value,)
        elif isinstance(tags_value, list):
            tags = tuple(str(tag) for tag in tags_value if tag)
        else:
            tags = ()

        items.append(
            build_news_item(
                source=source,
                url=url,
                canonical_url=field("canonical_url"),
                title=title,
                published_at=published,
                fetched_at=fetched_at,
                author=field("author"),
                language=field("language"),
                summary_raw=field("summary"),
                content_text=field("summary"),
                tags=tags,
                category_raw=field("category"),
                image_url=field("image_url"),
                image_alt=field("image_alt"),
            )
        )
    items.sort(key=lambda item: item.published_at or "", reverse=True)
    return items[:limit] if limit is not None else items


class ApiCollector(BaseCollector):
    def collect(
        self,
        source: SourceConfig,
        *,
        since_hours: int,
        limit: int,
        fetched_at: datetime | None = None,
    ) -> list[NewsItem]:
        if not source.api_url:
            raise ValueError(f"No API URL configured for {source.id}")
        fetched_at = fetched_at or datetime.now(timezone.utc)
        response = self.fetcher.get(source.api_url, allowed_domains=source.allowed_domains)
        return parse_api_response(
            response.json(), source, fetched_at, since_hours=since_hours, limit=limit
        )
