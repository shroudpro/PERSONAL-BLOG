from __future__ import annotations

import calendar
import time
from datetime import datetime, timedelta, timezone

import feedparser
from bs4 import BeautifulSoup

from news_pipeline.collectors.base import BaseCollector
from news_pipeline.core.models import NewsItem, SourceConfig, build_news_item
from news_pipeline.core.normalize import is_domain_allowed, normalize_datetime


def _entry_datetime(entry: object) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed is None:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def _entry_image(entry: object) -> tuple[str | None, str | None]:
    for key in ("media_content", "media_thumbnail", "enclosures", "links"):
        candidates = getattr(entry, key, None) or []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            url = candidate.get("url") or candidate.get("href")
            media_type = candidate.get("type", "").casefold()
            medium = candidate.get("medium", "").casefold()
            if url and ("image" in media_type or medium == "image" or key in {"media_content", "media_thumbnail"}):
                return str(url), candidate.get("title") or candidate.get("description")
    return None, None


def _html_snippet(value: str | None) -> str | None:
    if not value:
        return None
    return " ".join(BeautifulSoup(value, "html.parser").get_text(" ", strip=True).split()) or None


def parse_feed(
    raw: bytes,
    source: SourceConfig,
    fetched_at: datetime,
    *,
    since_hours: int,
    limit: int | None = None,
) -> list[NewsItem]:
    parsed = feedparser.parse(raw)
    entries = parsed.get("entries", [])
    if parsed.get("bozo") and not entries:
        raise ValueError(f"Could not parse feed for {source.id}: {parsed.get('bozo_exception')}")

    cutoff = fetched_at.astimezone(timezone.utc) - timedelta(hours=since_hours)
    items: list[NewsItem] = []
    for entry in entries:
        title = " ".join(str(entry.get("title", "")).split())
        link = entry.get("link") or entry.get("id")
        if not title or not link or not is_domain_allowed(link, source.allowed_domains):
            continue

        published = _entry_datetime(entry)
        if published and published < cutoff:
            continue

        snippet = _html_snippet(entry.get("summary") or entry.get("description"))
        image_url, image_alt = _entry_image(entry)
        categories = entry.get("tags") or []
        tags = tuple(str(tag.get("term", "")).strip() for tag in categories if tag.get("term"))
        category = tags[0] if tags else None
        author = entry.get("author")
        item = build_news_item(
            source=source,
            url=str(link),
            title=title,
            published_at=published,
            fetched_at=fetched_at,
            summary_raw=snippet,
            content_text=snippet,
            author=author,
            tags=tags,
            category_raw=category,
            image_url=image_url,
            image_alt=image_alt,
            image_source=source.homepage if image_url else None,
        )
        items.append(item)

    items.sort(key=lambda item: item.published_at or "", reverse=True)
    return items[:limit] if limit is not None else items


class FeedCollector(BaseCollector):
    def collect(
        self,
        source: SourceConfig,
        *,
        since_hours: int,
        limit: int,
        fetched_at: datetime | None = None,
    ) -> list[NewsItem]:
        fetched_at = fetched_at or datetime.now(timezone.utc)
        endpoints = source.feed_urls or ((source.feed_url,) if source.feed_url else ())
        if not endpoints:
            raise ValueError(f"No feed URL configured for {source.id}")

        items: list[NewsItem] = []
        for endpoint in endpoints:
            response = self.fetcher.get(endpoint, allowed_domains=source.allowed_domains)
            remaining = max(limit - len(items), 0)
            if remaining == 0:
                break
            items.extend(parse_feed(response.content, source, fetched_at, since_hours=since_hours, limit=remaining))
        unique: dict[str, NewsItem] = {}
        for item in items:
            unique.setdefault(item.canonical_url, item)
        return sorted(unique.values(), key=lambda item: item.published_at or "", reverse=True)[:limit]
