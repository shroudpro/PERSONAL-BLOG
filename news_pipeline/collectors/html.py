from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from news_pipeline.collectors.base import BaseCollector
from news_pipeline.core.models import NewsItem, SourceConfig, build_news_item
from news_pipeline.core.normalize import clean_text, is_domain_allowed


def _matches_url(url: str, patterns: tuple[str, ...]) -> bool:
    return not patterns or any(re.search(pattern, url) for pattern in patterns)


def extract_listing_links(html: str, source: SourceConfig, base_url: str | None = None) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    base_url = base_url or source.list_url or source.homepage
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        url = urljoin(base_url, anchor["href"].strip())
        path = urlsplit(url).path
        if not is_domain_allowed(url, source.allowed_domains):
            continue
        if not _matches_url(url, source.item_url_patterns):
            continue
        if any(re.search(pattern, url) for pattern in source.exclude_url_patterns):
            continue
        if url not in seen:
            seen.add(url)
            links.append(url)
    return links


def _json_ld_values(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, list):
        for child in value:
            yield from _json_ld_values(child)
    elif isinstance(value, dict):
        yield value
        for key in ("@graph", "mainEntity", "mainEntityOfPage"):
            if key in value:
                yield from _json_ld_values(value[key])


def _json_ld_items(soup: BeautifulSoup) -> Iterator[dict[str, Any]]:
    for script in soup.find_all("script", type=re.compile("ld\\+json", re.I)):
        try:
            data = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        yield from _json_ld_values(data)


def _meta(soup: BeautifulSoup, *selectors: tuple[str, str]) -> str | None:
    for attribute, value in selectors:
        node = soup.find("meta", attrs={attribute: value})
        if node and node.get("content"):
            return str(node["content"]).strip()
    return None


def _schema_value(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, dict):
        return value.get("url") or value.get("contentUrl") or value.get("name") or value.get("caption")
    return value


def _from_schema(items: list[dict[str, Any]], *keys: str) -> Any:
    for item in items:
        for key in keys:
            if item.get(key):
                return _schema_value(item[key])
    return None


def parse_article_page(
    html: str,
    url: str,
    source: SourceConfig,
    fetched_at: datetime,
    *,
    published_hint: str | None = None,
) -> NewsItem:
    soup = BeautifulSoup(html, "html.parser")
    schema = list(_json_ld_items(soup))
    canonical_node = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical_url = urljoin(url, canonical_node.get("href", "")) if canonical_node else url
    if not is_domain_allowed(canonical_url, source.allowed_domains):
        canonical_url = url

    h1 = soup.find("h1")
    title = (
        _meta(soup, ("property", "og:title"), ("name", "twitter:title"))
        or _from_schema(schema, "headline", "name")
        or (h1.get_text(" ", strip=True) if h1 else None)
        or (soup.title.get_text(" ", strip=True) if soup.title else None)
    )
    if not title:
        raise ValueError(f"No title found for {url}")

    summary = (
        _meta(soup, ("property", "og:description"), ("name", "description"), ("name", "twitter:description"))
        or _from_schema(schema, "description")
    )
    published = (
        _meta(soup, ("property", "article:published_time"), ("name", "datePublished"), ("name", "pubdate"))
        or _from_schema(schema, "datePublished", "dateCreated")
        or next((node.get("datetime") for node in soup.find_all("time") if node.get("datetime")), None)
        or published_hint
    )
    image_value = _from_schema(schema, "image")
    image_url = (
        _meta(soup, ("property", "og:image"), ("name", "twitter:image"))
        or (str(image_value) if image_value else None)
    )
    image_alt = _meta(soup, ("property", "og:image:alt"), ("name", "twitter:image:alt"))
    if image_url:
        image_url = urljoin(url, image_url)
    author = _meta(soup, ("name", "author")) or _from_schema(schema, "author")
    language = (soup.html.get("lang") if soup.html else None) or source.language
    categories = _meta(soup, ("property", "article:section"), ("name", "keywords"))
    category = clean_text(categories.split(",", 1)[0]) if categories else None

    return build_news_item(
        source=source,
        url=url,
        canonical_url=canonical_url,
        title=title,
        published_at=published,
        fetched_at=fetched_at,
        author=author,
        language=language,
        summary_raw=summary,
        content_text=summary,
        tags=tuple(part.strip() for part in categories.split(",") if part.strip()) if categories else (),
        category_raw=category,
        image_url=image_url,
        image_alt=image_alt,
        image_source=source.homepage if image_url else None,
    )


class HtmlCollector(BaseCollector):
    def collect(
        self,
        source: SourceConfig,
        *,
        since_hours: int,
        limit: int,
        fetched_at: datetime | None = None,
    ) -> list[NewsItem]:
        if not source.list_url:
            raise ValueError(f"No list URL configured for {source.id}")
        fetched_at = fetched_at or datetime.now(timezone.utc)
        listing = self.fetcher.get(source.list_url, allowed_domains=source.allowed_domains)
        links = extract_listing_links(listing.text, source, listing.url)[:limit]
        items: list[NewsItem] = []
        for item_url in links:
            response = self.fetcher.get(item_url, allowed_domains=source.allowed_domains)
            try:
                item = parse_article_page(response.text, response.url, source, fetched_at)
            except ValueError:
                continue
            items.append(item)
        cutoff = fetched_at.astimezone(timezone.utc).timestamp() - since_hours * 3600
        return [item for item in items if not item.published_at or datetime.fromisoformat(item.published_at.replace("Z", "+00:00")).timestamp() >= cutoff]
