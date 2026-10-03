from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from news_pipeline.core.models import FetchMethod, SourceConfig, SourceType
from news_pipeline.core.normalize import is_domain_allowed


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "sources.yml"
_SOURCE_TYPES = {"official", "research"}
_FETCH_METHODS = {"feed", "api", "sitemap", "html", "arxiv"}


def _strings(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a string or a list of strings")
    return tuple(item.strip() for item in value if item.strip())


def _validate_endpoint(source_id: str, url: str | None, domains: tuple[str, ...], field_name: str) -> None:
    if not url:
        return
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{source_id}.{field_name} must be an HTTP(S) URL")
    if not is_domain_allowed(url, domains):
        raise ValueError(f"{source_id}.{field_name} is outside allowed_domains: {url}")


def load_sources(path: str | Path | None = None) -> list[SourceConfig]:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not load source configuration {config_path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("sources"), list):
        raise ValueError("Source configuration must contain a 'sources' list")

    sources: list[SourceConfig] = []
    seen_ids: set[str] = set()
    for entry in raw["sources"]:
        if not isinstance(entry, dict):
            raise ValueError("Each source configuration must be a mapping")
        source_id = entry.get("id")
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id):
            raise ValueError(f"Invalid source id: {source_id!r}")
        if source_id in seen_ids:
            raise ValueError(f"Duplicate source id: {source_id}")
        seen_ids.add(source_id)

        source_type = entry.get("type")
        fetch_method = entry.get("fetch_method")
        if source_type not in _SOURCE_TYPES:
            raise ValueError(f"{source_id}.type must be one of {sorted(_SOURCE_TYPES)}")
        if fetch_method not in _FETCH_METHODS:
            raise ValueError(f"{source_id}.fetch_method must be one of {sorted(_FETCH_METHODS)}")

        domains = _strings(entry.get("allowed_domains"), field_name=f"{source_id}.allowed_domains")
        if not domains:
            raise ValueError(f"{source_id}.allowed_domains cannot be empty")
        source = SourceConfig(
            id=source_id,
            name=str(entry.get("name", "")).strip(),
            source_type=source_type,
            homepage=str(entry.get("homepage", "")).strip(),
            enabled=entry.get("enabled") is True,
            priority=int(entry.get("priority", 0)),
            fetch_method=fetch_method,
            allowed_domains=tuple(domain.casefold().lstrip(".") for domain in domains),
            default_tags=_strings(entry.get("default_tags"), field_name=f"{source_id}.default_tags"),
            notes=str(entry.get("notes", "")).strip(),
            language=entry.get("language"),
            feed_url=entry.get("feed_url"),
            feed_urls=_strings(entry.get("feed_urls"), field_name=f"{source_id}.feed_urls"),
            api_url=entry.get("api_url"),
            api_items_path=entry.get("api_items_path"),
            api_field_map=entry.get("api_field_map") or {},
            sitemap_urls=_strings(entry.get("sitemap_urls"), field_name=f"{source_id}.sitemap_urls"),
            list_url=entry.get("list_url"),
            item_url_patterns=_strings(entry.get("item_url_patterns"), field_name=f"{source_id}.item_url_patterns"),
            exclude_url_patterns=_strings(entry.get("exclude_url_patterns"), field_name=f"{source_id}.exclude_url_patterns"),
            categories=_strings(entry.get("categories"), field_name=f"{source_id}.categories"),
        )
        if not source.name or not source.homepage:
            raise ValueError(f"{source_id}.name and homepage are required")
        if not isinstance(entry.get("enabled"), bool):
            raise ValueError(f"{source_id}.enabled must be a boolean")
        if source.priority < 1:
            raise ValueError(f"{source_id}.priority must be positive")
        if not isinstance(source.api_field_map, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in source.api_field_map.items()
        ):
            raise ValueError(f"{source_id}.api_field_map must contain string paths")

        for field_name, endpoint in (("homepage", source.homepage), ("feed_url", source.feed_url), ("api_url", source.api_url), ("list_url", source.list_url)):
            _validate_endpoint(source_id, endpoint, source.allowed_domains, field_name)
        for field_name, endpoints in (("feed_urls", source.feed_urls), ("sitemap_urls", source.sitemap_urls)):
            for endpoint in endpoints:
                _validate_endpoint(source_id, endpoint, source.allowed_domains, field_name)

        if source.fetch_method in {"feed", "arxiv"} and not (source.feed_url or source.feed_urls):
            raise ValueError(f"{source_id} requires feed_url or feed_urls")
        if source.fetch_method == "api" and (not source.api_url or not source.api_items_path or not source.api_field_map):
            raise ValueError(f"{source_id} requires api_url, api_items_path and api_field_map")
        if source.fetch_method == "sitemap" and not source.sitemap_urls:
            raise ValueError(f"{source_id} requires sitemap_urls")
        if source.fetch_method == "html" and not source.list_url:
            raise ValueError(f"{source_id} requires list_url")
        for pattern in (*source.item_url_patterns, *source.exclude_url_patterns):
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"Invalid URL pattern for {source_id}: {pattern}") from exc
        sources.append(source)

    return sorted(sources, key=lambda source: (source.priority, source.id))
