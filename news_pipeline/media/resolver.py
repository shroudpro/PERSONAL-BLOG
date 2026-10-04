from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from news_pipeline.core.normalize import normalize_url
from news_pipeline.media.models import ImageCandidate


def _image_values(value: Any) -> list[tuple[str, str | None]]:
    if isinstance(value, str):
        return [(value, None)]
    if isinstance(value, list):
        return [entry for item in value for entry in _image_values(item)]
    if isinstance(value, dict):
        url = value.get("contentUrl") or value.get("url") or value.get("@id")
        alt = value.get("caption") or value.get("name") or value.get("description")
        if isinstance(url, str):
            return [(url, alt if isinstance(alt, str) else None)]
    return []


def _structured_images(value: Any) -> list[tuple[str, str | None]]:
    found: list[tuple[str, str | None]] = []
    if isinstance(value, list):
        for item in value:
            found.extend(_structured_images(item))
    elif isinstance(value, dict):
        for key in ("image", "thumbnailUrl", "primaryImageOfPage"):
            if key in value:
                found.extend(_image_values(value[key]))
        for key in ("@graph", "mainEntity", "mainEntityOfPage"):
            if key in value:
                found.extend(_structured_images(value[key]))
    return found


def _candidate(url: str, source_page: str, discovered_by: str, alt: str | None = None) -> ImageCandidate | None:
    resolved = urljoin(source_page, url.strip())
    try:
        normalized = normalize_url(resolved)
        normalized_page = normalize_url(source_page)
    except ValueError:
        return None
    if urlsplit(normalized).scheme != "https":
        return None
    return ImageCandidate(normalized, normalized_page, discovered_by, alt.strip() if alt else None)


def parse_image_candidates(
    html: str,
    source_page: str,
    *,
    feed_image_url: str | None = None,
    feed_image_alt: str | None = None,
) -> list[ImageCandidate]:
    """Parse image metadata in the documented priority order without downloading it."""
    soup = BeautifulSoup(html, "html.parser")
    raw_candidates: list[tuple[str, str | None, str]] = []

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.string or script.get_text()
        if not text.strip():
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue
        raw_candidates.extend((url, alt, "structured_data") for url, alt in _structured_images(data))

    for attrs, key, source in (
        (("property", "og:image"), "content", "og_image"),
        (("property", "og:image:url"), "content", "og_image"),
        (("name", "twitter:image"), "content", "twitter_image"),
        (("name", "twitter:image:src"), "content", "twitter_image"),
    ):
        element = soup.find("meta", attrs={attrs[0]: attrs[1]})
        if element and element.get(key):
            raw_candidates.append((element[key], None, source))

    if feed_image_url:
        raw_candidates.append((feed_image_url, feed_image_alt, "feed"))

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        path = urlsplit(href).path.casefold()
        label = f"{anchor.get_text(' ', strip=True)} {href}".casefold()
        if path.rsplit(".", 1)[-1] in {"png", "jpg", "jpeg", "webp"} and any(
            marker in label for marker in ("press", "media kit", "download", "press kit")
        ):
            raw_candidates.append((href, anchor.get("aria-label") or anchor.get_text(" ", strip=True), "press_media_kit"))

    candidates: list[ImageCandidate] = []
    seen: set[str] = set()
    for url, alt, discovered_by in raw_candidates:
        candidate = _candidate(url, source_page, discovered_by, alt)
        if candidate and candidate.url not in seen:
            seen.add(candidate.url)
            candidates.append(candidate)
    return candidates
