from datetime import datetime, timezone

from news_pipeline.cli import _print_rows, collect_sources
from news_pipeline.core.models import SourceConfig, build_news_item


def source(source_id: str, priority: int) -> SourceConfig:
    return SourceConfig(
        id=source_id,
        name=source_id.title(),
        source_type="official",
        homepage="https://example.com/",
        enabled=True,
        priority=priority,
        fetch_method="feed",
        allowed_domains=("example.com",),
    )


class StaticCollector:
    def __init__(self, source_config):
        self.source_config = source_config

    def collect(self, source, *, since_hours, limit, fetched_at=None):
        if source.id == "broken":
            raise RuntimeError("source is unavailable")
        return [
            build_news_item(
                source=source,
                url="https://example.com/news/item",
                title="A new item",
                published_at="2026-10-03T03:00:00Z",
                fetched_at=fetched_at,
                summary_raw="A source snippet.",
            )
        ]


def test_collection_continues_after_a_source_failure_and_dry_run_writes_nothing(tmp_path) -> None:
    sources = [source("broken", 1), source("healthy", 2)]

    result = collect_sources(
        sources,
        since_hours=24,
        limit=20,
        dry_run=True,
        pipeline_root=tmp_path,
        collector_factory=lambda source_config, _: StaticCollector(source_config),
        fetched_at=datetime(2026, 10, 3, 4, 0, tzinfo=timezone.utc),
    )

    assert result["exit_code"] == 1
    assert [row["status"] for row in result["rows"]] == ["FAIL", "PASS"]
    assert result["new_items"] == 1
    assert not (tmp_path / "storage" / "inbox").exists()
    assert not (tmp_path / "state" / "seen.jsonl").exists()


def test_cli_table_labels_are_localized_to_chinese(capsys) -> None:
    _print_rows(
        [
            {
                "source_name": "OpenAI",
                "status": "PASS",
                "method": "站点地图",
                "items": 1,
                "new_items": 1,
                "latest": "2026-10-03T03:00:00Z",
                "image": True,
            }
        ]
    )

    output = capsys.readouterr().out
    assert "来源" in output
    assert "状态" in output
    assert "最新时间（上海）" in output
