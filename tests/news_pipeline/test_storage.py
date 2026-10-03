import json
from datetime import datetime, timezone

import pytest

from news_pipeline.core.dedupe import DedupeIndex
from news_pipeline.core.models import SourceConfig, build_news_item
from news_pipeline.core.storage import InboxStore, SeenStateError


def item(url: str = "https://example.com/news/a", title: str = "A title", summary: str = "summary"):
    source = SourceConfig(
        id="sample",
        name="Sample",
        source_type="official",
        homepage="https://example.com/",
        enabled=True,
        priority=1,
        fetch_method="feed",
        allowed_domains=("example.com",),
    )
    return build_news_item(
        source=source,
        url=url,
        title=title,
        published_at="2026-10-02T12:00:00Z",
        fetched_at=datetime(2026, 10, 3, 4, 0, tzinfo=timezone.utc),
        summary_raw=summary,
    )


def test_dedupe_checks_canonical_url_then_title_then_content_hash() -> None:
    index = DedupeIndex()
    first = item()
    index.add(first)

    assert index.duplicate_reason(item(url="https://example.com/news/a?utm_source=feed")) == "canonical_url"
    assert index.duplicate_reason(item(url="https://example.com/news/b", title="A title")) == "normalized_title"
    assert index.duplicate_reason(item(url="https://example.com/news/c", title="Another title")) == "content_hash"


def test_inbox_store_writes_json_and_seen_state_idempotently(tmp_path) -> None:
    store = InboxStore(tmp_path)
    first = item()

    assert store.save([first]) == [first]
    assert store.save([first]) == []
    records = list((tmp_path / "storage" / "inbox").glob("*.json"))
    seen = tmp_path / "state" / "seen.jsonl"

    assert len(records) == 1
    assert json.loads(records[0].read_text(encoding="utf-8"))["id"] == first.id
    assert len(seen.read_text(encoding="utf-8").splitlines()) == 1


def test_inbox_store_rejects_corrupt_seen_state_without_overwriting(tmp_path) -> None:
    seen = tmp_path / "state" / "seen.jsonl"
    seen.parent.mkdir(parents=True)
    seen.write_text('{"id": "ok", "canonical_url": "https://example.com/ok"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(SeenStateError, match="line 2"):
        InboxStore(tmp_path).load_index()

    assert seen.read_text(encoding="utf-8") == '{"id": "ok", "canonical_url": "https://example.com/ok"}\nnot-json\n'


def test_dry_run_does_not_create_inbox_or_state(tmp_path) -> None:
    store = InboxStore(tmp_path)

    assert store.save([item()], dry_run=True) == [item()]
    assert not (tmp_path / "storage" / "inbox").exists()
    assert not (tmp_path / "state" / "seen.jsonl").exists()
