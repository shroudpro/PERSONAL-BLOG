from __future__ import annotations

import json
from datetime import datetime

import pytest
import yaml

from news_pipeline.editor.article import EditorArticle
from news_pipeline.publisher.jekyll import publish_articles


def make_article(
    *,
    news_id: str = "news-001",
    source_id: str = "google-ai",
    source_url: str = "https://example.com/news/model",
    slug: str = "model-release",
    category: str = "模型发布",
    image: str | None = "/assets/news/2026/10/model-release.webp",
    image_alt: str | None = "模型发布封面",
    image_source_url: str | None = None,
    body_markdown: str = "## 发生了什么\n\n模型已发布。\n\n## 来源\n\n[官方原文](https://example.com/news/model)\n",
) -> EditorArticle:
    return EditorArticle(
        news_id=news_id,
        source_id=source_id,
        source_name="Example AI",
        title="模型发布说明",
        slug=slug,
        date="2026-10-03T20:30:00+08:00",
        summary="官方发布了一个新模型。",
        category=category,
        tags=("Example AI", "模型发布"),
        source_url=source_url,
        source_published_at="2026-10-02T12:00:00Z",
        body_markdown=body_markdown,
        image=image,
        image_alt=image_alt,
        image_source_url=image_source_url,
    )


def write_draft(path, article: EditorArticle) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(article.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    if article.image and article.image.startswith("/assets/news/"):
        repository_root = path.parent.parent
        image_path = repository_root / article.image.lstrip("/")
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"test cover")
        manifest_path = repository_root / "assets" / "news" / "manifest.json"
        manifest_path.write_text(
            json.dumps({
                "schema_version": 1,
                "covers": [{"post_slug": article.slug, "local_path": article.image, "sha256": "test"}],
            }),
            encoding="utf-8",
        )


def test_publisher_dry_run_validates_and_writes_nothing(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    write_draft(draft_dir / "news-001.json", make_article())

    result = publish_articles(draft_dir, posts_dir, state_path, limit=5, dry_run=True)

    assert result["planned_count"] == 1
    assert result["published_count"] == 0
    assert not posts_dir.exists()
    assert not state_path.exists()


def test_publisher_writes_jekyll_post_and_idempotent_publication_state(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    write_draft(draft_dir / "news-001.json", make_article())

    result = publish_articles(draft_dir, posts_dir, state_path, limit=5)

    assert result["published_count"] == 1
    post_path = posts_dir / "2026-10-03-google-ai-model-release.md"
    assert post_path.is_file()
    source, body = post_path.read_text(encoding="utf-8").split("---\n", 2)[1:]
    front_matter = yaml.safe_load(source)
    assert front_matter["layout"] == "post"
    assert front_matter["categories"] == ["模型发布"]
    assert front_matter["ai_generated"] is True
    assert front_matter["reviewed"] is False
    assert "https://example.com/news/model" in body
    records = [json.loads(line) for line in state_path.read_text(encoding="utf-8").splitlines()]
    assert records == [result["records"][0]]

    repeated = publish_articles(draft_dir, posts_dir, state_path, limit=5)
    assert repeated["published_count"] == 0
    assert repeated["skipped_count"] == 1
    assert len(state_path.read_text(encoding="utf-8").splitlines()) == 1


def test_publisher_validates_entire_batch_before_writing(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    write_draft(draft_dir / "news-001.json", make_article())
    invalid = make_article(news_id="news-002", slug="bad-slug", category="其他")
    write_draft(draft_dir / "news-002.json", invalid)

    with pytest.raises(ValueError, match="category"):
        publish_articles(draft_dir, posts_dir, state_path, limit=5)

    assert not posts_dir.exists()
    assert not state_path.exists()


def test_publisher_rejects_duplicate_source_url_and_slug(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    write_draft(draft_dir / "news-001.json", make_article())
    write_draft(
        draft_dir / "news-002.json",
        make_article(news_id="news-002", source_url="https://example.com/news/other"),
    )

    with pytest.raises(ValueError, match="slug"):
        publish_articles(draft_dir, posts_dir, state_path, limit=5)

    assert not posts_dir.exists()
    assert not state_path.exists()


def test_publisher_rejects_duplicate_source_url_even_when_slugs_differ(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    write_draft(draft_dir / "news-001.json", make_article())
    write_draft(
        draft_dir / "news-002.json",
        make_article(news_id="news-002", slug="second-release"),
    )

    with pytest.raises(ValueError, match="duplicate source_url"):
        publish_articles(draft_dir, posts_dir, state_path, limit=5)

    assert not posts_dir.exists()
    assert not state_path.exists()


def test_publisher_rejects_invalid_or_naive_date(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    article = make_article()
    article = EditorArticle(**{**article.__dict__, "date": datetime(2026, 10, 3).isoformat()})
    write_draft(draft_dir / "news-001.json", article)

    with pytest.raises(ValueError, match="timezone"):
        publish_articles(draft_dir, posts_dir, state_path, limit=5)

    assert not posts_dir.exists()


def test_publisher_rejects_utc_date_when_jekyll_date_must_be_shanghai_local(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    article = make_article()
    article = EditorArticle(**{**article.__dict__, "date": "2026-10-03T12:30:00Z"})
    write_draft(draft_dir / "news-001.json", article)

    with pytest.raises(ValueError, match="Asia/Shanghai"):
        publish_articles(draft_dir, posts_dir, state_path, limit=5)

    assert not posts_dir.exists()
    assert not state_path.exists()


def test_publisher_requires_clickable_source_link_and_safe_source_id(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    article = make_article(
        source_id="../outside",
        body_markdown="## 发生了什么\n\n模型已发布。\n\n来源：https://example.com/news/model\n",
    )
    write_draft(draft_dir / "news-001.json", article)

    with pytest.raises(ValueError, match="source_id|clickable"):
        publish_articles(draft_dir, posts_dir, state_path, limit=5)

    assert not (tmp_path / "outside-model-release.md").exists()
    assert not state_path.exists()


def test_publisher_rejects_remote_or_missing_cover(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    remote = make_article(image="https://cdn.example.com/cover.png", image_alt="remote")
    write_draft(draft_dir / "news-001.json", remote)

    with pytest.raises(ValueError, match="local /assets/news"):
        publish_articles(draft_dir, posts_dir, state_path, limit=5)

    missing = make_article(image=None, image_alt=None)
    write_draft(draft_dir / "news-001.json", missing)
    with pytest.raises(ValueError, match="image is required"):
        publish_articles(draft_dir, posts_dir, state_path, limit=5)


def test_publisher_rejects_cover_missing_from_manifest(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    article = make_article()
    draft_dir.mkdir(parents=True)
    (draft_dir / "news-001.json").write_text(
        json.dumps(article.to_dict(), ensure_ascii=False), encoding="utf-8"
    )
    image_path = tmp_path / article.image.lstrip("/")
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"test cover")
    manifest_path = tmp_path / "assets" / "news" / "manifest.json"
    manifest_path.write_text(json.dumps({"schema_version": 1, "covers": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="missing from cover manifest"):
        publish_articles(draft_dir, posts_dir, state_path, limit=5)


def test_publisher_accepts_equivalent_source_url_with_trailing_slash(tmp_path) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    article = make_article(
        body_markdown=(
            "## 发生了什么\n\n模型已发布。\n\n"
            "## 来源\n\n[官方原文](https://example.com/news/model/)\n"
        ),
    )
    write_draft(draft_dir / "news-001.json", article)

    result = publish_articles(draft_dir, posts_dir, state_path, limit=5, dry_run=True)

    assert result["planned_count"] == 1


@pytest.mark.parametrize("tags", [(), ("one-tag",), ("one", "two", "three", "four", "five", "six")])
def test_publisher_rejects_tag_count_outside_taxonomy_bounds(tmp_path, tags) -> None:
    draft_dir = tmp_path / "editor_drafts"
    posts_dir = tmp_path / "_posts"
    state_path = tmp_path / "state" / "publications.jsonl"
    article = make_article()
    article = EditorArticle(**{**article.__dict__, "tags": tags})
    write_draft(draft_dir / "news-001.json", article)

    with pytest.raises(ValueError, match="tags"):
        publish_articles(draft_dir, posts_dir, state_path, limit=5)

    assert not posts_dir.exists()
    assert not state_path.exists()
