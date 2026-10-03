import json
from datetime import datetime, timezone

from news_pipeline.cli import _print_rows, collect_sources
from news_pipeline.cli import build_parser, run_edit, run_publish
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


def test_cli_parser_supports_edit_and_publish_dry_runs() -> None:
    parser = build_parser()

    edit_args = parser.parse_args(["edit", "--limit", "7", "--select", "news-001", "--select", "news-002", "--dry-run"])
    publish_args = parser.parse_args(["publish", "--limit", "5", "--dry-run"])

    assert (edit_args.command, edit_args.limit, edit_args.dry_run) == ("edit", 7, True)
    assert edit_args.select_news_ids == ["news-001", "news-002"]
    assert (publish_args.command, publish_args.limit, publish_args.dry_run) == ("publish", 5, True)


def test_edit_dry_run_does_not_write_report_or_drafts(tmp_path) -> None:
    inbox_dir = tmp_path / "storage" / "inbox"
    inbox_dir.mkdir(parents=True)
    source_config = source("official-ai", 1)
    news_item = build_news_item(
        source=source_config,
        url="https://example.com/news/model",
        title="Introducing a new AI model for coding agents",
        summary_raw="The model adds tool use for software engineering workflows.",
        published_at="2026-10-02T12:00:00Z",
        fetched_at=datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
    )
    (inbox_dir / "item.json").write_text(json.dumps(news_item.to_dict()), encoding="utf-8")

    result = run_edit(
        pipeline_root=tmp_path,
        limit=1,
        dry_run=True,
        now=datetime(2026, 10, 3, 20, tzinfo=timezone.utc),
    )

    assert result["selected_count"] == 1
    assert not (tmp_path / "reports" / "editor_selection.md").exists()
    assert not (tmp_path / "storage" / "editor_drafts").exists()


def test_edit_persists_report_and_never_overwrites_existing_draft(tmp_path) -> None:
    inbox_dir = tmp_path / "storage" / "inbox"
    inbox_dir.mkdir(parents=True)
    source_config = source("official-ai", 1)
    news_item = build_news_item(
        source=source_config,
        url="https://example.com/news/model",
        title="Introducing a new AI model for coding agents",
        summary_raw="The model adds tool use for software engineering workflows.",
        published_at="2026-10-02T12:00:00Z",
        fetched_at=datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
    )
    (inbox_dir / "item.json").write_text(json.dumps(news_item.to_dict()), encoding="utf-8")
    draft_dir = tmp_path / "storage" / "editor_drafts"
    draft_dir.mkdir(parents=True)
    existing_draft = draft_dir / f"{news_item.id}.json"
    existing_draft.write_text('{"hand_edited": true}\n', encoding="utf-8")

    result = run_edit(
        pipeline_root=tmp_path,
        limit=1,
        dry_run=False,
        now=datetime(2026, 10, 3, 20, tzinfo=timezone.utc),
    )

    assert result["selected_count"] == 1
    assert (tmp_path / "reports" / "editor_selection.md").is_file()
    assert existing_draft.read_text(encoding="utf-8") == '{"hand_edited": true}\n'


def test_publish_cli_dry_run_keeps_publication_files_unchanged(tmp_path) -> None:
    from news_pipeline.editor.article import EditorArticle

    draft_dir = tmp_path / "storage" / "editor_drafts"
    draft_dir.mkdir(parents=True)
    article = EditorArticle(
        news_id="news-001",
        source_id="official-ai",
        source_name="Official AI",
        title="A verified model update",
        slug="verified-model-update",
        date="2026-10-03T20:30:00+08:00",
        summary="An official model update.",
        category="模型发布",
        tags=("Official AI", "LLM"),
        source_url="https://example.com/news/model",
        source_published_at="2026-10-02T12:00:00Z",
        body_markdown="## 发生了什么\n\n更新内容。\n\n## 来源\n\n[官方原文](https://example.com/news/model)\n",
    )
    (draft_dir / "news-001.json").write_text(json.dumps(article.to_dict()), encoding="utf-8")
    repo_dir = tmp_path / "repo"

    result = run_publish(
        pipeline_root=tmp_path,
        repository_root=repo_dir,
        limit=5,
        dry_run=True,
    )

    assert result["planned_count"] == 1
    assert not (repo_dir / "_posts").exists()
    assert not (tmp_path / "state" / "publications.jsonl").exists()
