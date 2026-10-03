from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from news_pipeline.core.normalize import normalize_url, parse_datetime_value
from news_pipeline.editor.article import EditorArticle
from news_pipeline.editor.taxonomy import CATEGORIES


_SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\((https?://[^)\s]+)\)")
_SHANGHAI = ZoneInfo("Asia/Shanghai")


def validate_article(article: EditorArticle) -> list[str]:
    errors: list[str] = []
    if not article.title.strip():
        errors.append("title must not be empty")
    if not _SLUG_PATTERN.fullmatch(article.source_id):
        errors.append("source_id must contain lowercase ASCII letters, digits, and single hyphens")
    if not _SLUG_PATTERN.fullmatch(article.slug):
        errors.append("slug must contain lowercase ASCII letters, digits, and single hyphens")
    try:
        parsed_date = datetime.fromisoformat(article.date.replace("Z", "+00:00"))
    except ValueError:
        parsed_date = None
    if parsed_date is None or parsed_date.tzinfo is None or parsed_date.utcoffset() is None:
        errors.append("date must be a valid timezone-aware timestamp")
    elif parsed_date.utcoffset() != timedelta(hours=8):
        errors.append("date must represent Asia/Shanghai local time")
    if not article.summary.strip():
        errors.append("summary must not be empty")
    if article.category not in CATEGORIES:
        errors.append(f"category is not in the allowed taxonomy: {article.category!r}")
    if not 2 <= len(article.tags) <= 5:
        errors.append("tags must contain between 2 and 5 values")
    normalized_tags = [tag.strip().casefold() for tag in article.tags]
    if any(not tag for tag in normalized_tags) or len(normalized_tags) != len(set(normalized_tags)):
        errors.append("tags must be non-empty and unique")
    if not article.source_name.strip():
        errors.append("source_name must not be empty")
    try:
        normalized_source_url = normalize_url(article.source_url)
    except ValueError:
        normalized_source_url = None
        errors.append("source_url must be a valid HTTP(S) URL")
    if article.source_published_at is not None and parse_datetime_value(article.source_published_at) is None:
        errors.append("source_published_at must be a valid timestamp or null")
    if not article.body_markdown.strip():
        errors.append("body must not be empty")
    else:
        linked_source_urls: set[str] = set()
        for match in _MARKDOWN_LINK_PATTERN.finditer(article.body_markdown):
            try:
                linked_source_urls.add(normalize_url(match.group(1)))
            except ValueError:
                continue
        if normalized_source_url is None or normalized_source_url not in linked_source_urls:
            errors.append("body must include a clickable Markdown link to source_url")
    if article.image is not None and article.image.strip():
        errors.append("image is not enabled for this MVP without confirmed reuse rights")
    return errors


def validate_article_batch(
    articles: Iterable[EditorArticle],
    *,
    publication_records: Iterable[dict] = (),
    existing_post_paths: Iterable[Path] = (),
    existing_source_urls: Iterable[str] = (),
) -> list[str]:
    article_list = list(articles)
    errors: list[str] = []
    seen_news_ids: set[str] = set()
    seen_source_urls: set[str] = set()
    seen_slugs: set[str] = set()
    normalized_existing_urls: set[str] = set()
    for url in existing_source_urls:
        try:
            normalized_existing_urls.add(normalize_url(url))
        except ValueError:
            errors.append(f"invalid source_url in existing _posts: {url}")

    for article in article_list:
        errors.extend(f"{article.news_id}: {error}" for error in validate_article(article))
        if article.news_id in seen_news_ids:
            errors.append(f"duplicate news_id: {article.news_id}")
        seen_news_ids.add(article.news_id)
        try:
            source_url = normalize_url(article.source_url)
        except ValueError:
            source_url = article.source_url
        if source_url in seen_source_urls:
            errors.append(f"duplicate source_url: {article.source_url}")
        if source_url in normalized_existing_urls:
            errors.append(f"source_url is already present in _posts: {article.source_url}")
        seen_source_urls.add(source_url)
        slug_key = article.slug.casefold()
        if slug_key in seen_slugs:
            errors.append(f"duplicate slug: {article.slug}")
        seen_slugs.add(slug_key)

    published_ids = {str(record.get("news_id", "")) for record in publication_records}
    published_urls = set()
    for record in publication_records:
        value = record.get("source_url")
        if isinstance(value, str):
            try:
                published_urls.add(normalize_url(value))
            except ValueError:
                errors.append(f"invalid source_url in publication state: {value}")
    for article in article_list:
        if article.news_id in published_ids:
            errors.append(f"news_id is already published: {article.news_id}")
        try:
            source_url = normalize_url(article.source_url)
        except ValueError:
            continue
        if source_url in published_urls:
            errors.append(f"source_url is already published: {article.source_url}")

    existing_stems = {path.stem.casefold() for path in existing_post_paths}
    for article in article_list:
        date_value = parse_datetime_value(article.date)
        if date_value is None:
            continue
        post_stem = f"{date_value.astimezone(_SHANGHAI):%Y-%m-%d}-{article.source_id}-{article.slug}".casefold()
        if post_stem in existing_stems:
            errors.append(f"post path already exists: {post_stem}.md")
    return errors
