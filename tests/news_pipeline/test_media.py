from __future__ import annotations

import io
import json

import pytest
import yaml
from PIL import Image

from news_pipeline.media.fallback import render_fallback_cover
from news_pipeline.media.manifest import CoverManifest
from news_pipeline.media.models import ImageCandidate
from news_pipeline.media.processor import process_image_bytes
from news_pipeline.media.resolver import parse_image_candidates
from news_pipeline.media.validator import load_image_permissions, permission_for, validate_image_bytes
from news_pipeline.editor.article import EditorArticle
from news_pipeline.media.pipeline import prepare_covers
from news_pipeline.core.fetch import FetchError


def _png_bytes(size: tuple[int, int] = (80, 40), color: str = "#f00") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


def test_resolver_orders_structured_metadata_before_social_and_feed_images() -> None:
    html = """
    <html><head>
      <script type="application/ld+json">
        {"@type":"NewsArticle","image":{"url":"/structured.webp","caption":"Structured"}}
      </script>
      <meta property="og:image" content="/open-graph.png">
      <meta name="twitter:image" content="/twitter.jpg">
    </head></html>
    """

    candidates = parse_image_candidates(
        html,
        "https://publisher.example/news/story",
        feed_image_url="https://cdn.publisher.example/feed.webp",
        feed_image_alt="Feed cover",
    )

    assert [candidate.discovered_by for candidate in candidates] == [
        "structured_data", "og_image", "twitter_image", "feed"
    ]
    assert candidates[0].url == "https://publisher.example/structured.webp"
    assert candidates[0].alt == "Structured"
    assert candidates[-1].source_page == "https://publisher.example/news/story"


def test_reuse_permission_requires_explicit_source_page_and_asset_prefix(tmp_path) -> None:
    permission_path = tmp_path / "image_reuse.yml"
    permission_path.write_text(
        yaml.safe_dump({
            "approved_assets": [{
                "source_id": "google-ai",
                "source_page": "https://blog.google/story/",
                "asset_url_prefix": "https://storage.googleapis.com/press-kit/",
                "reuse_basis": "CC BY 4.0",
                "evidence_url": "https://blog.google/press/license/",
            }]
        }),
        encoding="utf-8",
    )
    permissions = load_image_permissions(permission_path)
    allowed = ImageCandidate("https://storage.googleapis.com/press-kit/hero.png", "https://blog.google/story/", "og_image")
    wrong_asset = ImageCandidate("https://storage.googleapis.com/user-upload/hero.png", "https://blog.google/story/", "og_image")
    wrong_page = ImageCandidate("https://storage.googleapis.com/press-kit/hero.png", "https://blog.google/other/", "og_image")

    assert permission_for(allowed, "google-ai", permissions) is not None
    assert permission_for(wrong_asset, "google-ai", permissions) is None
    assert permission_for(wrong_page, "google-ai", permissions) is None
    assert permission_for(allowed, "anthropic", permissions) is None


def test_image_validation_rejects_html_and_oversized_responses() -> None:
    with pytest.raises(ValueError, match="Content-Type"):
        validate_image_bytes(b"<html>not an image</html>", "text/html")
    with pytest.raises(ValueError, match="size"):
        validate_image_bytes(_png_bytes(), "image/png", max_bytes=4)


def test_image_processing_rotates_resizes_and_removes_exif() -> None:
    source = Image.new("RGB", (40, 80), "#336699")
    exif = source.getexif()
    exif[274] = 6
    buffer = io.BytesIO()
    source.save(buffer, format="JPEG", exif=exif)

    output = process_image_bytes(buffer.getvalue())
    image = Image.open(io.BytesIO(output))

    assert image.format == "WEBP"
    assert image.size == (1280, 720)
    assert not image.getexif()


def test_fallback_cover_is_a_webp_and_changes_with_article_text() -> None:
    first = render_fallback_cover(title="模型更新：面向复杂工作流", source_name="来源", category="模型发布", date="2026-10-04")
    second = render_fallback_cover(title="另一个模型更新", source_name="来源", category="模型发布", date="2026-10-04")
    image = Image.open(io.BytesIO(first))

    assert image.format == "WEBP"
    assert image.size == (1280, 720)
    assert first != second


def test_manifest_reuses_same_sha256_asset_for_multiple_articles(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest = CoverManifest(manifest_path)
    first = manifest.add(
        post_slug="first-story", local_path="/assets/news/2026/10/first-story.webp",
        original_url=None, source_page=None, sha256="same", width=1280, height=720,
        generated=True, reuse_basis="generated fallback", evidence_url=None,
    )
    second = manifest.add(
        post_slug="second-story", local_path="/assets/news/2026/10/second-story.webp",
        original_url=None, source_page=None, sha256="same", width=1280, height=720,
        generated=True, reuse_basis="generated fallback", evidence_url=None,
    )
    manifest.save()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert first["local_path"] == second["local_path"]
    assert len(payload["covers"]) == 2


def test_prepare_covers_dry_run_is_side_effect_free_and_real_run_updates_draft(tmp_path) -> None:
    pipeline_root = tmp_path / "news_pipeline"
    draft_dir = pipeline_root / "storage" / "editor_drafts"
    draft_dir.mkdir(parents=True)
    draft = EditorArticle(
        news_id="news-001", source_id="google-ai", source_name="Google AI",
        title="一个新的 AI 模型", slug="new-ai-model", date="2026-10-04T12:00:00+08:00",
        summary="摘要", category="模型发布", tags=("AI", "模型"),
        source_url="https://example.com/news/model", source_published_at="2026-10-04T00:00:00Z",
        body_markdown="[官方原文](https://example.com/news/model)",
    )
    draft_path = draft_dir / "news-001.json"
    draft_path.write_text(json.dumps(draft.to_dict(), ensure_ascii=False), encoding="utf-8")
    repository_root = tmp_path / "repository"

    preview = prepare_covers(repository_root, pipeline_root, dry_run=True)
    assert preview["count"] == 1
    assert not (repository_root / "assets").exists()
    assert json.loads(draft_path.read_text(encoding="utf-8"))["image"] is None

    result = prepare_covers(repository_root, pipeline_root)
    payload = json.loads(draft_path.read_text(encoding="utf-8"))
    assert result["count"] == 1
    assert payload["image"].startswith("/assets/news/")
    assert (repository_root / payload["image"].lstrip("/")).is_file()
    assert json.loads((repository_root / "assets/news/manifest.json").read_text(encoding="utf-8"))["covers"]


def test_prepare_covers_falls_back_when_permitted_download_fails(tmp_path) -> None:
    pipeline_root = tmp_path / "news_pipeline"
    draft_dir = pipeline_root / "storage" / "editor_drafts"
    draft_dir.mkdir(parents=True)
    draft = EditorArticle(
        news_id="news-002", source_id="google-ai", source_name="Google AI",
        title="带候选图的 AI 资讯", slug="ai-with-candidate", date="2026-10-04T12:00:00+08:00",
        summary="摘要", category="模型发布", tags=("AI", "模型"),
        source_url="https://example.com/news/candidate", source_published_at="2026-10-04T00:00:00Z",
        body_markdown="[官方原文](https://example.com/news/candidate)",
    )
    (draft_dir / "news-002.json").write_text(json.dumps(draft.to_dict()), encoding="utf-8")
    inbox_dir = pipeline_root / "storage" / "inbox"
    inbox_dir.mkdir(parents=True)
    inbox_dir.joinpath("news-002.json").write_text(json.dumps({
        "id": "news-002", "source_id": "google-ai", "source_name": "Google AI",
        "source_type": "official", "title": draft.title, "url": draft.source_url,
        "canonical_url": draft.source_url, "published_at": "2026-10-04T00:00:00Z",
        "fetched_at": "2026-10-04T01:00:00Z", "image_url": "https://cdn.example.com/press/hero.png",
        "image_alt": "官方候选图", "image_source": draft.source_url,
    }), encoding="utf-8")
    permission_path = pipeline_root / "config" / "image_reuse.yml"
    permission_path.parent.mkdir(parents=True)
    permission_path.write_text(yaml.safe_dump({"approved_assets": [{
        "source_id": "google-ai", "source_page": draft.source_url,
        "asset_url_prefix": "https://cdn.example.com/press/", "reuse_basis": "明确授权",
        "evidence_url": "https://example.com/license",
    }]}), encoding="utf-8")

    class FailingFetcher:
        def get(self, *args, **kwargs):
            raise FetchError("network failure")

    result = prepare_covers(
        tmp_path / "repository", pipeline_root,
        fetcher=FailingFetcher(), permission_path=permission_path,
    )

    assert result["records"][0]["generated"] is True
    assert result["records"][0]["original_url"] is None
