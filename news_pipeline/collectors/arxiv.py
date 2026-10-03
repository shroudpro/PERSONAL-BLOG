from __future__ import annotations

from datetime import datetime

from news_pipeline.collectors.base import BaseCollector
from news_pipeline.collectors.feed import parse_feed
from news_pipeline.core.models import NewsItem, SourceConfig


class ArxivCollector(BaseCollector):
    def collect(
        self,
        source: SourceConfig,
        *,
        since_hours: int,
        limit: int,
        fetched_at: datetime | None = None,
    ) -> list[NewsItem]:
        from datetime import timezone

        fetched_at = fetched_at or datetime.now(timezone.utc)
        endpoints = source.feed_urls or ((source.feed_url,) if source.feed_url else ())
        if not endpoints:
            raise ValueError(f"No arXiv RSS feed URLs configured for {source.id}")

        items: dict[str, NewsItem] = {}
        for endpoint in endpoints:
            response = self.fetcher.get(endpoint, allowed_domains=source.allowed_domains)
            for item in parse_feed(response.content, source, fetched_at, since_hours=since_hours, limit=limit):
                items.setdefault(item.canonical_url, item)
        return sorted(items.values(), key=lambda item: item.published_at or "", reverse=True)[:limit]
