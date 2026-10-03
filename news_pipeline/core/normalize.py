from __future__ import annotations

import calendar
import html
import re
import time
import unicodedata
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from time import struct_time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_TRACKING_KEYS = {
    "dclid",
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "ref",
    "ref_src",
    "srsltid",
    "spm",
    "ved",
    "yclid",
}


def normalize_url(url: str) -> str:
    """Remove fragments and common tracking parameters from an HTTP URL."""
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    if scheme not in {"http", "https"} or not hostname:
        raise ValueError(f"Unsupported URL: {url!r}")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URLs with embedded credentials are not allowed")

    port = parsed.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = parsed.path.rstrip("/") or "/"
    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        normalized_key = key.casefold()
        if normalized_key.startswith("utm_") or normalized_key in _TRACKING_KEYS:
            continue
        query_items.append((key, value))
    query_items.sort(key=lambda pair: (pair[0].casefold(), pair[1]))
    return urlunsplit((scheme, netloc, path, urlencode(query_items, doseq=True), ""))


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", html.unescape(title)).casefold()
    characters = [" " if unicodedata.category(char).startswith("P") else char for char in normalized]
    return " ".join("".join(characters).split())


def normalize_datetime(value: str | datetime | date | struct_time | None) -> str | None:
    if value is None or value == "":
        return None

    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, struct_time):
        parsed = datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    elif isinstance(value, str):
        candidate = value.strip()
        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(candidate)
            except (TypeError, ValueError, OverflowError):
                return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def is_domain_allowed(url: str, allowed_domains: tuple[str, ...] | list[str]) -> bool:
    hostname = (urlsplit(url).hostname or "").casefold().rstrip(".")
    return any(
        hostname == domain.casefold().rstrip(".")
        or hostname.endswith("." + domain.casefold().rstrip("."))
        for domain in allowed_domains
    )


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    normalized = " ".join(html.unescape(value).split())
    return normalized or None


def parse_datetime_value(value: str | datetime | date | struct_time | None) -> datetime | None:
    normalized = normalize_datetime(value)
    if normalized is None:
        return None
    return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
