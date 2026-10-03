from __future__ import annotations

from datetime import datetime, timezone

from news_pipeline.core.models import SourceConfig, build_news_item
from news_pipeline.editor.article import EditorArticle
from news_pipeline.editor.selector import select_candidates
from news_pipeline.editor.taxonomy import CATEGORIES


def make_item(
    *,
    title: str,
    summary: str,
    published_at: str | None,
    source_id: str = "official-ai",
    url: str | None = None,
):
    source = SourceConfig(
        id=source_id,
        name=source_id.replace("-", " ").title(),
        source_type="official",
        homepage="https://example.com/",
        enabled=True,
        priority=1,
        fetch_method="feed",
        allowed_domains=("example.com",),
        default_tags=("AI",),
    )
    return build_news_item(
        source=source,
        url=url or f"https://example.com/{source_id}/{title.lower().replace(' ', '-')}",
        title=title,
        summary_raw=summary,
        published_at=published_at,
        fetched_at=datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
    )


def test_editor_article_round_trips_to_json_shape() -> None:
    item = make_item(
        title="A model update",
        summary="A useful release for AI developers.",
        published_at="2026-10-02T12:00:00Z",
    )
    article = EditorArticle.from_news_item(
        item,
        date="2026-10-03T20:00:00+08:00",
        slug="model-update",
    )

    restored = EditorArticle.from_dict(article.to_dict())

    assert restored == article
    assert restored.news_id == item.id
    assert restored.tags == ()
    assert "body_markdown" in restored.to_dict()


def test_selector_prefers_recent_substantive_news_and_marks_duplicates() -> None:
    model_release = make_item(
        title="Introducing a new AI model for coding agents",
        summary="The model adds tool use and longer context for software engineering workflows.",
        published_at="2026-10-02T12:00:00Z",
        source_id="model-lab",
    )
    duplicate = make_item(
        title="A new AI model for coding agents",
        summary="The same model adds tool use and longer context for software engineering workflows.",
        published_at="2026-10-02T11:00:00Z",
        source_id="research-lab",
    )
    stale_marketing = make_item(
        title="Join our AI event this spring",
        summary="Register for our upcoming event and product showcase.",
        published_at="2026-04-01T12:00:00Z",
        source_id="event-source",
    )

    decisions = select_candidates(
        [stale_marketing, duplicate, model_release],
        limit=1,
        now=datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
    )

    selected = [decision for decision in decisions if decision.selected]
    dropped_duplicate = next(decision for decision in decisions if decision.item.id == duplicate.id)
    dropped_stale = next(decision for decision in decisions if decision.item.id == stale_marketing.id)
    assert [decision.item.id for decision in selected] == [model_release.id]
    assert "重复" in " ".join(dropped_duplicate.reasons)
    assert "时效" in " ".join(dropped_stale.reasons)


def test_taxonomy_contains_only_the_phase_two_categories() -> None:
    assert CATEGORIES == (
        "模型发布",
        "产品更新",
        "研究进展",
        "开源项目",
        "AI 工具",
        "AI 基础设施",
        "安全与治理",
        "行业动态",
    )


def test_selector_does_not_match_generic_tags_or_substrings_as_editorial_signals() -> None:
    item = make_item(
        title="A local weather update",
        summary="The forecast prevents delays in relevant planning work.",
        published_at="2026-10-02T12:00:00Z",
    )

    decision = select_candidates(
        [item],
        limit=1,
        now=datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
    )[0]

    assert decision.dimensions["AI 相关性"] == 1
    assert "活动或营销信息" not in " ".join(decision.reasons)


def test_selector_prefers_source_specific_original_when_deduplicating() -> None:
    deepmind_original = make_item(
        title="Introducing SynthID Bio for synthetic biology",
        summary="SynthID Bio is a watermarking method for synthetic biology.",
        published_at="2026-09-30T15:00:00Z",
        source_id="google-deepmind",
        url="https://deepmind.google/blog/introducing-synthid-bio/",
    )
    google_cross_post = make_item(
        title="Introducing SynthID Bio for synthetic biology",
        summary="SynthID Bio is a watermarking method for synthetic biology.",
        published_at="2026-09-30T15:00:00Z",
        source_id="google-ai",
        url="https://blog.google/innovation/synthid-bio/",
    )

    decisions = select_candidates(
        [google_cross_post, deepmind_original],
        limit=1,
        now=datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
    )

    assert [decision.item.id for decision in decisions if decision.selected] == [deepmind_original.id]


def test_selector_allows_an_explicit_editorial_selection() -> None:
    ranked_first = make_item(
        title="An AI model launch with benchmark results",
        summary="A new model for research and developer tools.",
        published_at="2026-10-03T10:00:00Z",
    )
    editor_choice = make_item(
        title="A research infrastructure milestone",
        summary="A prototype satellite entered orbit for a long-term machine learning research project.",
        published_at="2026-10-01T10:00:00Z",
    )

    decisions = select_candidates(
        [ranked_first, editor_choice],
        limit=1,
        now=datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
        selected_news_ids={editor_choice.id},
    )

    assert [decision.item.id for decision in decisions if decision.selected] == [editor_choice.id]
    chosen = next(decision for decision in decisions if decision.item.id == editor_choice.id)
    assert "人工指定" in " ".join(chosen.reasons)
