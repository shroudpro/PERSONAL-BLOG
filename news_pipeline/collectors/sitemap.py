from __future__ import annotations

import gzip
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from xml.etree import ElementTree

from news_pipeline.collectors.base import BaseCollector
from news_pipeline.collectors.html import parse_article_page
from news_pipeline.core.models import NewsItem, SourceConfig
from news_pipeline.core.normalize import is_domain_allowed, parse_datetime_value


def parse_sitemap(raw: bytes) -> tuple[list[tuple[str, str | None]], list[str]]:
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    root = ElementTree.fromstring(raw)
    local = lambda tag: tag.rsplit("}", 1)[-1]
    if local(root.tag) not in {"urlset", "sitemapindex"}:
        raise ValueError(f"Unsupported sitemap root element: {local(root.tag)}")

    entries: list[tuple[str, str | None]] = []
    children: list[str] = []
    for node in root:
        node_type = local(node.tag)
        fields = {local(child.tag): child for child in node}
        location = fields.get("loc")
        if location is None or not location.text:
            continue
        if node_type == "sitemap":
            children.append(location.text.strip())
            continue
        lastmod = fields.get("lastmod")
        published = None
        for nested in node.iter():
            if local(nested.tag) == "publication_date" and nested.text:
                published = nested.text.strip()
                break
        entries.append((location.text.strip(), (published or (lastmod.text.strip() if lastmod is not None and lastmod.text else None))))
    return entries, children


class SitemapCollector(BaseCollector):
    def _read_sitemap(
        self,
        url: str,
        source: SourceConfig,
        *,
        visited: set[str],
        depth: int,
    ) -> list[tuple[str, str | None]]:
        if url in visited:
            return []
        if depth > 2:
            raise ValueError(f"Sitemap nesting is too deep for {source.id}")
        if not is_domain_allowed(url, source.allowed_domains):
            raise ValueError(f"Sitemap URL is outside the allowed domains for {source.id}: {url}")
        visited.add(url)
        response = self.fetcher.get(url, allowed_domains=source.allowed_domains)
        entries, children = parse_sitemap(response.content)
        for child in children:
            entries.extend(self._read_sitemap(child, source, visited=visited, depth=depth + 1))
        return entries

    def collect(
        self,
        source: SourceConfig,
        *,
        since_hours: int,
        limit: int,
        fetched_at: datetime | None = None,
    ) -> list[NewsItem]:
        if not source.sitemap_urls:
            raise ValueError(f"No sitemap URL configured for {source.id}")
        fetched_at = fetched_at or datetime.now(timezone.utc)
        cutoff = fetched_at.astimezone(timezone.utc) - timedelta(hours=since_hours)
        entries: dict[str, str | None] = {}
        visited: set[str] = set()
        for sitemap_url in source.sitemap_urls:
            for url, lastmod in self._read_sitemap(sitemap_url, source, visited=visited, depth=0):
                if not is_domain_allowed(url, source.allowed_domains):
                    continue
                if source.item_url_patterns and not any(re.search(pattern, url) for pattern in source.item_url_patterns):
                    continue
                if any(re.search(pattern, url) for pattern in source.exclude_url_patterns):
                    continue
                changed_at = parse_datetime_value(lastmod) if lastmod else None
                if changed_at and changed_at < cutoff:
                    continue
                entries.setdefault(url, lastmod)

        candidates = sorted(
            entries.items(),
            key=lambda pair: parse_datetime_value(pair[1]) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )[:limit]
        items: list[NewsItem] = []
        for url, lastmod in candidates:
            try:
                response = self.fetcher.get(url, allowed_domains=source.allowed_domains)
                item = parse_article_page(response.text, response.url, source, fetched_at, published_hint=lastmod)
            except (ValueError, RuntimeError) as exc:
                continue
            if item.published_at:
                published_at = datetime.fromisoformat(item.published_at.replace("Z", "+00:00"))
                if published_at < cutoff:
                    continue
            items.append(item)
        items.sort(key=lambda item: item.published_at or "", reverse=True)
        return items[:limit]
