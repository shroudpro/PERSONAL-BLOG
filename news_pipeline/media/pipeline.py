from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import yaml

from news_pipeline.core.fetch import FetchError, HttpFetcher
from news_pipeline.core.config import load_sources
from news_pipeline.core.models import NewsItem
from news_pipeline.core.normalize import normalize_url, parse_datetime_value
from news_pipeline.editor.article import EditorArticle
from news_pipeline.media.downloader import download_image
from news_pipeline.media.fallback import render_fallback_cover
from news_pipeline.media.manifest import CoverManifest
from news_pipeline.media.models import ImageCandidate
from news_pipeline.media.processor import process_image_bytes
from news_pipeline.media.resolver import parse_image_candidates
from news_pipeline.media.validator import load_image_permissions, permission_for


SHANGHAI = ZoneInfo("Asia/Shanghai")
_FRONT_MATTER_SPLIT = "---\n"


@dataclass(frozen=True)
class CoverTarget:
    news_id: str
    source_id: str
    source_name: str
    title: str
    slug: str
    category: str
    date: str
    source_url: str
    image_url: str | None
    image_alt: str | None
    image_source: str | None
    draft_path: Path | None = None
    post_path: Path | None = None


def _atomic_text(path: Path, text: str) -> None:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as file:
            file.write(text)
            temporary_path = Path(file.name)
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
        raise


def _read_front_matter(path: Path) -> tuple[dict[str, Any], str]:
    content = path.read_text(encoding="utf-8")
    if not content.startswith(_FRONT_MATTER_SPLIT):
        raise ValueError(f"Missing YAML front matter: {path}")
    parts = content.split(_FRONT_MATTER_SPLIT, 2)
    if len(parts) != 3:
        raise ValueError(f"Invalid YAML front matter: {path}")
    payload = yaml.safe_load(parts[1])
    if not isinstance(payload, dict):
        raise ValueError(f"Front matter must be a mapping: {path}")
    return payload, parts[2]


def _render_front_matter(path: Path, payload: dict[str, Any], body: str) -> None:
    text = _FRONT_MATTER_SPLIT + yaml.safe_dump(
        payload, allow_unicode=True, default_flow_style=False, sort_keys=False, width=1000,
    ) + _FRONT_MATTER_SPLIT + body
    _atomic_text(path, text)


def _slug_from_post(path: Path, source_id: str) -> str:
    prefix = f"{path.stem[:10]}-{source_id}-"
    if path.stem.startswith(prefix):
        return path.stem[len(prefix):]
    return re.sub(r"[^a-z0-9]+", "-", path.stem.casefold()).strip("-")


def _source_id_from_post(path: Path, configured_ids: tuple[str, ...]) -> str:
    stem_without_date = path.stem[11:] if re.match(r"^\d{4}-\d{2}-\d{2}-", path.stem) else path.stem
    for source_id in sorted(configured_ids, key=len, reverse=True):
        if stem_without_date.startswith(f"{source_id}-"):
            return source_id
    return stem_without_date.split("-", 1)[0]


def _date_string(value: Any) -> str:
    parsed = parse_datetime_value(value)
    if parsed is None:
        return datetime.now(SHANGHAI).isoformat(timespec="seconds")
    return parsed.astimezone(SHANGHAI).isoformat(timespec="seconds")


def _validate_slug(slug: str) -> str:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError(f"Invalid article slug for cover path: {slug}")
    return slug


def _cover_directory(date: str) -> str:
    parsed = parse_datetime_value(date)
    if parsed is None:
        raise ValueError(f"Invalid article date for cover path: {date}")
    local = parsed.astimezone(SHANGHAI)
    return f"{local:%Y/%m}"


def _validate_local_path(local_path: str) -> str:
    path = PurePosixPath(local_path)
    if (
        not local_path.startswith("/assets/news/")
        or path.is_absolute() is False
        or ".." in path.parts
        or path.suffix.casefold() != ".webp"
    ):
        raise ValueError(f"Invalid local cover path: {local_path}")
    return local_path


def _find_news_item(source_url: str, inbox_items: list[NewsItem]) -> NewsItem | None:
    normalized = normalize_url(source_url)
    return next(
        (item for item in inbox_items if normalize_url(item.canonical_url) == normalized),
        None,
    )


def load_cover_targets(
    repository_root: str | Path,
    pipeline_root: str | Path,
    *,
    news_ids: set[str] | None = None,
) -> list[CoverTarget]:
    repository_root = Path(repository_root)
    pipeline_root = Path(pipeline_root)
    requested = news_ids or set()
    inbox_items: list[NewsItem] = []
    inbox_dir = pipeline_root / "storage" / "inbox"
    if inbox_dir.exists():
        for item_path in sorted(inbox_dir.glob("*.json")):
            inbox_items.append(NewsItem(**json.loads(item_path.read_text(encoding="utf-8"))))

    targets: list[CoverTarget] = []
    source_config_path = pipeline_root / "config" / "sources.yml"
    configured_source_ids = tuple(
        source.id for source in load_sources(source_config_path)
    ) if source_config_path.exists() else ()
    draft_dir = pipeline_root / "storage" / "editor_drafts"
    if draft_dir.exists():
        for draft_path in sorted(draft_dir.glob("*.json")):
            article = EditorArticle.from_dict(json.loads(draft_path.read_text(encoding="utf-8")))
            if requested and article.news_id not in requested:
                continue
            target_item = _find_news_item(article.source_url, inbox_items)
            targets.append(CoverTarget(
                news_id=article.news_id,
                source_id=article.source_id,
                source_name=article.source_name,
                title=article.title,
                slug=article.slug,
                category=article.category or "AI 资讯",
                date=article.date,
                source_url=article.source_url,
                image_url=target_item.image_url if target_item else None,
                image_alt=target_item.image_alt if target_item else article.image_alt,
                image_source=target_item.image_source if target_item else article.image_source_url,
                draft_path=draft_path,
            ))

    publication_path = pipeline_root / "state" / "publications.jsonl"
    if publication_path.exists():
        for line in publication_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            news_id = str(record["news_id"])
            if requested and news_id not in requested:
                continue
            post_path = repository_root / record["post_path"]
            if not post_path.exists():
                continue
            front_matter, _ = _read_front_matter(post_path)
            source_url = str(front_matter.get("source_url") or record["source_url"])
            item = _find_news_item(source_url, inbox_items)
            source_id = item.source_id if item else _source_id_from_post(post_path, configured_source_ids)
            targets.append(CoverTarget(
                news_id=news_id,
                source_id=source_id,
                source_name=str(front_matter.get("source_name") or (item.source_name if item else source_id)),
                title=str(front_matter.get("title") or post_path.stem),
                slug=_slug_from_post(post_path, source_id),
                category=str((front_matter.get("categories") or ["AI 资讯"])[0]),
                date=_date_string(front_matter.get("date") or record.get("published_local_at")),
                source_url=source_url,
                image_url=item.image_url if item else None,
                image_alt=item.image_alt if item else front_matter.get("image_alt"),
                image_source=item.image_source if item else front_matter.get("image_source_url"),
                post_path=post_path,
            ))

    unique: dict[str, CoverTarget] = {}
    for target in targets:
        existing = unique.get(target.news_id)
        if existing is None:
            unique[target.news_id] = target
        else:
            # A published article and its editor draft share one news ID; one cover
            # preparation must update both representations atomically at the end.
            # Prefer the draft's source identity and candidate metadata: the post
            # filename cannot unambiguously recover source IDs that contain '-'.
            unique[target.news_id] = replace(
                existing,
                draft_path=existing.draft_path or target.draft_path,
                post_path=existing.post_path or target.post_path,
                image_url=existing.image_url or target.image_url,
                image_alt=existing.image_alt or target.image_alt,
                image_source=existing.image_source or target.image_source,
            )
    return sorted(unique.values(), key=lambda target: target.news_id)


def _candidates_for(
    target: CoverTarget,
    fetcher: HttpFetcher,
    allowed_domains: tuple[str, ...],
) -> list[ImageCandidate]:
    feed_values = {
        "feed_image_url": target.image_url,
        "feed_image_alt": target.image_alt,
    }
    if allowed_domains:
        try:
            response = fetcher.get(target.source_url, allowed_domains=allowed_domains)
        except FetchError:
            response = None
        if response is not None:
            return parse_image_candidates(response.text, target.source_url, **feed_values)
    if not target.image_url:
        return []
    # The article URL is the auditable page where the candidate is used;
    # collector image_source values can point at a feed or site homepage.
    return [ImageCandidate(
        url=target.image_url,
        source_page=target.source_url,
        discovered_by="feed",
        alt=target.image_alt,
    )]


def _write_binary(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as file:
            file.write(payload)
            temporary_path = Path(file.name)
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
        raise


def _update_draft(target: CoverTarget, image: str, alt: str, source_url: str | None) -> None:
    if not target.draft_path:
        return
    payload = json.loads(target.draft_path.read_text(encoding="utf-8"))
    payload["image"] = image
    payload["image_alt"] = alt
    payload["image_source_url"] = source_url
    _atomic_text(target.draft_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _update_post(target: CoverTarget, image: str, alt: str, source_url: str | None) -> None:
    if not target.post_path:
        return
    front_matter, body = _read_front_matter(target.post_path)
    front_matter["image"] = image
    front_matter["image_alt"] = alt
    front_matter["image_source_url"] = source_url or ""
    _render_front_matter(target.post_path, front_matter, body)


def prepare_covers(
    repository_root: str | Path,
    pipeline_root: str | Path,
    *,
    news_ids: set[str] | None = None,
    dry_run: bool = False,
    fetcher: HttpFetcher | None = None,
    permission_path: str | Path | None = None,
) -> dict[str, Any]:
    repository_root = Path(repository_root)
    pipeline_root = Path(pipeline_root)
    targets = load_cover_targets(repository_root, pipeline_root, news_ids=news_ids)
    if news_ids:
        found = {target.news_id for target in targets}
        missing = sorted(news_ids - found)
        if missing:
            raise ValueError(f"Unknown news IDs: {', '.join(missing)}")
    permissions = load_image_permissions(
        permission_path or pipeline_root / "config" / "image_reuse.yml"
    )
    fetcher = fetcher or HttpFetcher(timeout=(5, 15), max_retries=2)
    source_config_path = pipeline_root / "config" / "sources.yml"
    source_domains = (
        {source.id: source.allowed_domains for source in load_sources(source_config_path)}
        if source_config_path.exists()
        else {}
    )
    manifest = CoverManifest(repository_root / "assets" / "news" / "manifest.json")
    results: list[dict[str, Any]] = []

    for target in targets:
        _validate_slug(target.slug)
        candidates = _candidates_for(
            target,
            fetcher,
            source_domains.get(target.source_id, ()),
        )
        generated = True
        original_url: str | None = None
        source_page: str | None = None
        reuse_basis = "generated fallback"
        evidence_url: str | None = None
        payload: bytes | None = None
        for candidate in candidates:
            permission = permission_for(candidate, target.source_id, permissions)
            if permission is None:
                continue
            try:
                host = urlsplit(candidate.url).hostname
                if not host:
                    raise ValueError("candidate image URL has no hostname")
                raw_payload, _ = download_image(
                    fetcher,
                    candidate.url,
                    allowed_domains=(host,),
                    allowed_url_prefixes=(permission.asset_url_prefix,),
                )
                payload = process_image_bytes(raw_payload)
                generated = False
                original_url = candidate.url
                source_page = candidate.source_page
                reuse_basis = permission.reuse_basis
                evidence_url = permission.evidence_url
                break
            except (FetchError, OSError, ValueError):
                continue
        if payload is None:
            payload = render_fallback_cover(
                title=target.title, source_name=target.source_name,
                category=target.category, date=target.date,
            )

        digest = hashlib.sha256(payload).hexdigest()
        existing = manifest.by_sha256(digest)
        local_path = existing["local_path"] if existing else (
            f"/assets/news/{_cover_directory(target.date)}/{target.slug}.webp"
        )
        _validate_local_path(local_path)
        asset_path = repository_root / local_path.lstrip("/")
        record = {
            "post_slug": target.slug,
            "local_path": local_path,
            "original_url": original_url,
            "source_page": source_page,
            "sha256": digest,
            "width": 1280,
            "height": 720,
            "generated": generated,
            "reuse_basis": reuse_basis,
            "evidence_url": evidence_url,
        }
        results.append({**record, "news_id": target.news_id, "title": target.title})
        if not dry_run:
            if not asset_path.exists() or hashlib.sha256(asset_path.read_bytes()).hexdigest() != digest:
                _write_binary(asset_path, payload)
            manifest.add(**record)
            if generated:
                # A rejected official candidate must not provide the alt text for
                # the generated gradient; describe the asset that was actually saved.
                alt = f"{target.source_name}：{target.title}（{target.category}，AI 资讯封面）"
            else:
                alt = target.image_alt or f"{target.source_name}：{target.title}"
            _update_draft(target, local_path, alt, original_url)
            _update_post(target, local_path, alt, original_url)

    if not dry_run:
        manifest.save()
    return {"count": len(results), "dry_run": dry_run, "records": results}
