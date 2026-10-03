from datetime import datetime, timezone

from news_pipeline.core.models import SourceConfig, build_news_item
from news_pipeline.core.normalize import normalize_datetime, normalize_title, normalize_url


def source_config() -> SourceConfig:
    return SourceConfig(
        id="openai",
        name="OpenAI",
        source_type="official",
        homepage="https://openai.com/",
        enabled=True,
        priority=1,
        fetch_method="feed",
        allowed_domains=("openai.com",),
        default_tags=("AI",),
        language="en",
    )


def test_normalize_url_removes_tracking_and_keeps_content_parameters() -> None:
    normalized = normalize_url(
        "HTTPS://OpenAI.com/news/?id=42&utm_source=mail&fbclid=abc#section"
    )

    assert normalized == "https://openai.com/news?id=42"


def test_normalize_title_folds_spacing_punctuation_and_unicode() -> None:
    assert normalize_title("  ＧＰＴ—5:  New   Model! ") == "gpt 5 new model"


def test_normalize_datetime_converts_offset_to_utc_iso8601() -> None:
    assert normalize_datetime("2026-10-03T12:00:00+08:00") == "2026-10-03T04:00:00Z"
    assert normalize_datetime(None) is None


def test_build_news_item_uses_canonical_url_hash_and_utc_timestamps() -> None:
    item = build_news_item(
        source=source_config(),
        url="https://openai.com/news/example?utm_source=feed",
        canonical_url="https://openai.com/news/example/",
        title="Example announcement",
        published_at="2026-10-03T12:00:00+08:00",
        fetched_at=datetime(2026, 10, 3, 4, 1, tzinfo=timezone.utc),
        summary_raw="A short source summary.",
        content_text=None,
        tags=("research",),
    )

    assert item.id == "d5efd5125fa5ee78"
    assert item.canonical_url == "https://openai.com/news/example"
    assert item.published_at == "2026-10-03T04:00:00Z"
    assert item.fetched_at == "2026-10-03T04:01:00Z"
    assert item.tags_raw == ["AI", "research"]
    assert item.status == "collected"
