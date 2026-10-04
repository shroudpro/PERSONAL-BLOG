from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from news_pipeline.core.normalize import normalize_url, parse_datetime_value
from news_pipeline.editor.article import EditorArticle
from news_pipeline.editor.validator import validate_article_batch
from news_pipeline.media.manifest import CoverManifest


_SHANGHAI = ZoneInfo("Asia/Shanghai")
_PUBLICATION_FIELDS = {"news_id", "post_path", "source_url", "published_local_at"}


def load_publications(path: str | Path) -> list[dict[str, Any]]:
    state_path = Path(path)
    if not state_path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = state_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Could not read publication state {state_path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {state_path} at line {line_number}") from exc
        if not isinstance(record, dict) or not _PUBLICATION_FIELDS.issubset(record):
            raise ValueError(f"Invalid publication record in {state_path} at line {line_number}")
        if not all(isinstance(record[field], str) and record[field].strip() for field in _PUBLICATION_FIELDS):
            raise ValueError(f"Invalid publication record in {state_path} at line {line_number}")
        try:
            normalize_url(record["source_url"])
        except ValueError as exc:
            raise ValueError(f"Invalid source_url in {state_path} at line {line_number}") from exc
        if parse_datetime_value(record["published_local_at"]) is None:
            raise ValueError(f"Invalid published_local_at in {state_path} at line {line_number}")
        records.append(record)
    return records


def _load_drafts(draft_dir: Path) -> list[EditorArticle]:
    if not draft_dir.exists():
        return []
    articles: list[EditorArticle] = []
    seen_ids: set[str] = set()
    for draft_path in sorted(draft_dir.glob("*.json")):
        try:
            payload = json.loads(draft_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read editor draft {draft_path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Editor draft must contain a JSON object: {draft_path}")
        article = EditorArticle.from_dict(payload)
        if draft_path.stem != article.news_id:
            raise ValueError(f"Draft filename must match news_id: {draft_path}")
        if article.news_id in seen_ids:
            raise ValueError(f"Duplicate draft news_id: {article.news_id}")
        seen_ids.add(article.news_id)
        articles.append(article)
    return articles


def _read_existing_posts(posts_dir: Path) -> tuple[list[Path], list[str]]:
    paths = sorted(posts_dir.glob("*.md")) if posts_dir.exists() else []
    source_urls: list[str] = []
    for post_path in paths:
        try:
            content = post_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Could not read existing Jekyll post {post_path}: {exc}") from exc
        if not content.startswith("---\n"):
            continue
        parts = content.split("---\n", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid YAML front matter in existing post {post_path}")
        try:
            front_matter = yaml.safe_load(parts[1])
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML front matter in existing post {post_path}: {exc}") from exc
        if isinstance(front_matter, dict) and isinstance(front_matter.get("source_url"), str):
            source_urls.append(front_matter["source_url"])
    return paths, source_urls


def _post_path(posts_dir: Path, article: EditorArticle) -> Path:
    date_value = parse_datetime_value(article.date)
    if date_value is None:
        raise ValueError(f"{article.news_id}: date must be a valid timestamp")
    filename = f"{date_value.astimezone(_SHANGHAI):%Y-%m-%d}-{article.source_id}-{article.slug}.md"
    return posts_dir / filename


def render_post(article: EditorArticle) -> str:
    date_value = parse_datetime_value(article.date)
    if date_value is None:
        raise ValueError(f"{article.news_id}: date must be a valid timestamp")
    front_matter = {
        "layout": "post",
        "title": article.title,
        "date": date_value.astimezone(_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S %z"),
        "summary": article.summary,
        "categories": [article.category],
        "tags": list(article.tags),
        "image": article.image or "",
        "image_alt": article.image_alt or article.title,
        "image_source_url": article.image_source_url or "",
        "source_name": article.source_name,
        "source_url": article.source_url,
        "source_published_at": article.source_published_at or "",
        "ai_generated": True,
        "reviewed": False,
        "toc": True,
    }
    yaml_text = yaml.safe_dump(
        front_matter,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    )
    body = article.body_markdown.rstrip() + "\n"
    return f"---\n{yaml_text}---\n\n{body}"


def _publication_record(article: EditorArticle, post_path: Path, posts_dir: Path) -> dict[str, str]:
    date_value = parse_datetime_value(article.date)
    if date_value is None:
        raise ValueError(f"{article.news_id}: date must be a valid timestamp")
    return {
        "news_id": article.news_id,
        "post_path": f"_posts/{post_path.relative_to(posts_dir).as_posix()}",
        "source_url": article.source_url,
        "published_local_at": date_value.astimezone(_SHANGHAI).isoformat(timespec="seconds"),
    }


def _write_temporary(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_file.write(content)
        return Path(temporary_file.name)


def _write_state(path: Path, records: list[dict[str, str]]) -> None:
    content = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    temporary_path: Path | None = None
    try:
        temporary_path = _write_temporary(path, content)
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
        raise


def publish_articles(
    draft_dir: str | Path,
    posts_dir: str | Path,
    publication_path: str | Path,
    *,
    limit: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("limit must be positive")
    draft_dir = Path(draft_dir)
    posts_dir = Path(posts_dir)
    publication_path = Path(publication_path)
    state_records = load_publications(publication_path)
    drafts = _load_drafts(draft_dir)

    published_ids = {record["news_id"] for record in state_records}
    published_urls = {normalize_url(record["source_url"]) for record in state_records}
    pending = []
    skipped_count = 0
    for article in drafts:
        if article.news_id in published_ids or normalize_url(article.source_url) in published_urls:
            skipped_count += 1
        else:
            pending.append(article)
    pending.sort(
        key=lambda article: (
            parse_datetime_value(article.source_published_at)
            or parse_datetime_value(article.date)
            or datetime.min.replace(tzinfo=timezone.utc),
            article.news_id,
        ),
        reverse=True,
    )
    selected = pending[:limit]
    existing_paths, existing_urls = _read_existing_posts(posts_dir)
    errors = validate_article_batch(
        selected,
        publication_records=state_records,
        existing_post_paths=existing_paths,
        existing_source_urls=existing_urls,
    )
    targets = [_post_path(posts_dir, article) for article in selected]
    manifest = CoverManifest(posts_dir.parent / "assets" / "news" / "manifest.json")
    for article in selected:
        if not article.image:
            continue
        image_path = posts_dir.parent / article.image.lstrip("/")
        record = manifest.by_slug(article.slug)
        if not image_path.is_file():
            errors.append(f"{article.news_id}: local cover file does not exist: {article.image}")
        if record is None or record.get("local_path") != article.image:
            errors.append(f"{article.news_id}: image is missing from cover manifest: {article.image}")
    for article, target in zip(selected, targets):
        if target.exists():
            errors.append(f"post path already exists: {target.name}")
    if errors:
        raise ValueError("Article validation failed:\n- " + "\n- ".join(errors))

    new_records = [
        _publication_record(article, target, posts_dir)
        for article, target in zip(selected, targets)
    ]
    if dry_run or not selected:
        return {
            "planned_count": len(selected),
            "published_count": 0,
            "skipped_count": skipped_count,
            "records": new_records,
        }

    temporary_files: list[tuple[Path, Path]] = []
    written_paths: list[Path] = []
    try:
        for article, target in zip(selected, targets):
            temporary_files.append((
                _write_temporary(target, render_post(article)),
                target,
            ))
        for temporary_path, target in temporary_files:
            if target.exists():
                raise FileExistsError(f"post path appeared during publish: {target}")
            os.replace(temporary_path, target)
            written_paths.append(target)
        _write_state(publication_path, [*state_records, *new_records])
    except OSError:
        for temporary_path, _ in temporary_files:
            if temporary_path.exists():
                temporary_path.unlink()
        for written_path in written_paths:
            if written_path.exists():
                written_path.unlink()
        raise

    return {
        "planned_count": len(selected),
        "published_count": len(new_records),
        "skipped_count": skipped_count,
        "records": new_records,
    }
