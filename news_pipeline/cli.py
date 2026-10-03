from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from news_pipeline.collectors.api import ApiCollector
from news_pipeline.collectors.arxiv import ArxivCollector
from news_pipeline.collectors.base import BaseCollector
from news_pipeline.collectors.feed import FeedCollector
from news_pipeline.collectors.html import HtmlCollector
from news_pipeline.collectors.sitemap import SitemapCollector
from news_pipeline.core.config import load_sources
from news_pipeline.core.dedupe import DedupeIndex
from news_pipeline.core.fetch import HttpFetcher
from news_pipeline.core.models import NewsItem, SourceConfig
from news_pipeline.core.storage import InboxStore
from news_pipeline.editor.article import EditorArticle
from news_pipeline.editor.selector import render_selection_report, select_candidates
from news_pipeline.publisher.jekyll import load_publications, publish_articles


LOGGER = logging.getLogger("news_pipeline")
PIPELINE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PIPELINE_ROOT.parent
SHANGHAI = ZoneInfo("Asia/Shanghai")
_METHOD_LABELS = {
    "feed": "RSS/Atom",
    "api": "API",
    "sitemap": "站点地图",
    "html": "HTML",
    "arxiv": "arXiv RSS",
}


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("请输入正整数") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("请输入正整数")
    return parsed


def _article_slug(title: str, news_id: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.casefold()).strip("-")
    return slug[:64].rstrip("-") or f"news-{news_id}"


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
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
            temporary_path = temporary_file.name
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path and Path(temporary_path).exists():
            Path(temporary_path).unlink()
        raise


def _load_inbox_items(pipeline_root: Path) -> list[NewsItem]:
    inbox_dir = pipeline_root / "storage" / "inbox"
    if not inbox_dir.exists():
        return []
    items = []
    for item_path in sorted(inbox_dir.glob("*.json")):
        try:
            payload = json.loads(item_path.read_text(encoding="utf-8"))
            items.append(NewsItem(**payload))
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"Invalid inbox item {item_path}: {exc}") from exc
    return items


def run_edit(
    *,
    pipeline_root: str | Path = PIPELINE_ROOT,
    limit: int = 10,
    dry_run: bool = False,
    now: datetime | None = None,
    selected_news_ids: set[str] | None = None,
) -> dict:
    if limit < 1:
        raise ValueError("limit must be positive")
    pipeline_root = Path(pipeline_root)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    publication_records = load_publications(pipeline_root / "state" / "publications.jsonl")
    draft_dir = pipeline_root / "storage" / "editor_drafts"
    existing_draft_ids = {path.stem for path in draft_dir.glob("*.json")} if draft_dir.exists() else set()
    items = _load_inbox_items(pipeline_root)
    decisions = select_candidates(
        items,
        limit=limit,
        now=now,
        published_records=publication_records,
        existing_draft_ids=existing_draft_ids,
        selected_news_ids=selected_news_ids,
    )
    report = render_selection_report(decisions, now=now)
    selected = [decision for decision in decisions if decision.selected]
    if not dry_run:
        _atomic_write_text(pipeline_root / "reports" / "editor_selection.md", report)
        local_date = now.astimezone(SHANGHAI).isoformat(timespec="seconds")
        for decision in selected:
            draft_path = draft_dir / f"{decision.item.id}.json"
            if draft_path.exists():
                continue
            article = EditorArticle.from_news_item(
                decision.item,
                date=local_date,
                slug=_article_slug(decision.item.title, decision.item.id),
            )
            content = json.dumps(article.to_dict(), ensure_ascii=False, indent=2) + "\n"
            _atomic_write_text(draft_path, content)
    return {
        "candidate_count": len(items),
        "selected_count": len(selected),
        "report": report,
        "report_path": pipeline_root / "reports" / "editor_selection.md",
        "draft_dir": draft_dir,
    }


def run_publish(
    *,
    pipeline_root: str | Path = PIPELINE_ROOT,
    repository_root: str | Path = REPOSITORY_ROOT,
    limit: int = 5,
    dry_run: bool = False,
) -> dict:
    pipeline_root = Path(pipeline_root)
    repository_root = Path(repository_root)
    return publish_articles(
        pipeline_root / "storage" / "editor_drafts",
        repository_root / "_posts",
        pipeline_root / "state" / "publications.jsonl",
        limit=limit,
        dry_run=dry_run,
    )


def build_collector(source: SourceConfig, fetcher: HttpFetcher) -> BaseCollector:
    collectors: dict[str, type[BaseCollector]] = {
        "feed": FeedCollector,
        "api": ApiCollector,
        "sitemap": SitemapCollector,
        "html": HtmlCollector,
        "arxiv": ArxivCollector,
    }
    return collectors[source.fetch_method](fetcher)


def collect_sources(
    sources: list[SourceConfig],
    *,
    since_hours: int = 24,
    limit: int = 20,
    dry_run: bool = False,
    pipeline_root: str | Path = PIPELINE_ROOT,
    fetcher: HttpFetcher | None = None,
    collector_factory: Callable[[SourceConfig, HttpFetcher], BaseCollector] = build_collector,
    fetched_at: datetime | None = None,
) -> dict:
    if since_hours < 1 or limit < 1:
        raise ValueError("since_hours and limit must be positive")
    fetched_at = fetched_at or datetime.now(timezone.utc)
    fetcher = fetcher or HttpFetcher()
    store = InboxStore(pipeline_root)
    index = store.load_index()
    rows: list[dict] = []
    new_items = []

    for source in sorted(sources, key=lambda item: (item.priority, item.id)):
        if not source.enabled:
            continue
        row = {
            "source_id": source.id,
            "source_name": source.name,
            "method": _METHOD_LABELS[source.fetch_method],
            "status": "PASS",
            "items": 0,
            "new_items": 0,
            "latest": None,
            "image": False,
            "error": None,
        }
        try:
            collector = collector_factory(source, fetcher)
            items = collector.collect(
                source,
                since_hours=since_hours,
                limit=limit,
                fetched_at=fetched_at,
            )
            row["items"] = len(items)
            row["latest"] = max((item.published_at for item in items if item.published_at), default=None)
            row["image"] = any(item.image_url for item in items)
            for item in items:
                if index.add(item):
                    new_items.append(item)
                    row["new_items"] += 1
        except Exception as exc:
            row["status"] = "FAIL"
            row["error"] = str(exc)
            LOGGER.error("来源 %s 采集失败：%s", source.name, exc)
        rows.append(row)

    if not dry_run and new_items:
        stored = store.save(new_items)
        stored_ids = {item.id for item in stored}
        for row in rows:
            row["new_items"] = sum(
                1 for item in new_items if item.source_id == row["source_id"] and item.id in stored_ids
            )

    return {
        "rows": rows,
        "new_items": len(new_items),
        "exit_code": 1 if any(row["status"] == "FAIL" for row in rows) else 0,
    }


def check_sources(
    sources: list[SourceConfig],
    *,
    pipeline_root: str | Path = PIPELINE_ROOT,
    fetcher: HttpFetcher | None = None,
    collector_factory: Callable[[SourceConfig, HttpFetcher], BaseCollector] = build_collector,
    fetched_at: datetime | None = None,
) -> dict:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    fetcher = fetcher or HttpFetcher()
    rows: list[dict] = []
    for source in sorted(sources, key=lambda item: (item.priority, item.id)):
        if not source.enabled:
            continue
        row = {
            "source_id": source.id,
            "source_name": source.name,
            "method": _METHOD_LABELS[source.fetch_method],
            "status": "WARN",
            "items": 0,
            "latest": None,
            "image": False,
            "detail": "",
        }
        try:
            collector = collector_factory(source, fetcher)
            items = collector.collect(source, since_hours=168, limit=3, fetched_at=fetched_at)
            window_hours = 168
            if not items:
                items = collector.collect(source, since_hours=720, limit=3, fetched_at=fetched_at)
                window_hours = 720
            row["items"] = len(items)
            dated_items = [item for item in items if item.published_at]
            row["latest"] = max((item.published_at for item in dated_items), default=None)
            row["image"] = any(item.image_url for item in items)
            if not items:
                row["detail"] = "最近 30 天未解析到条目"
            elif not dated_items:
                row["detail"] = "条目缺少可解析的发布日期"
            elif window_hours == 720:
                row["detail"] = "7 天无更新，30 天内有条目"
            else:
                row["status"] = "PASS"
                row["detail"] = "标题、URL、日期可解析"
        except Exception as exc:
            row["status"] = "FAIL"
            row["detail"] = str(exc)
            LOGGER.error("来源 %s 健康检查失败：%s", source.name, exc)
        rows.append(row)
    return {"rows": rows, "exit_code": 1 if any(row["status"] == "FAIL" for row in rows) else 0}


def _display_time(value: str | None) -> str:
    if not value:
        return "—"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M")


def _print_rows(rows: list[dict], *, health: bool = False) -> None:
    columns = ["来源", "状态", "方式", "条目数", "最新时间（上海）", "图片"]
    if not health:
        columns.insert(4, "新增")
    widths = [22, 8, 11, 7, 21, 7] if health else [22, 8, 11, 7, 7, 21, 7]
    print("  ".join(value.ljust(width) for value, width in zip(columns, widths)))
    for row in rows:
        values = [
            row["source_name"],
            row["status"],
            row["method"],
            str(row["items"]),
        ]
        if not health:
            values.append(str(row["new_items"]))
        values.extend((_display_time(row.get("latest")), "YES" if row.get("image") else "NO"))
        print("  ".join(value[:width].ljust(width) for value, width in zip(values, widths)))
        if row.get("error") or row.get("detail"):
            print(f"  {row.get('error') or row.get('detail')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PERSONAL-BLOG 本地 AI 资讯编辑与采集工具")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="采集最近新增的资讯到本地 inbox")
    collect.add_argument("--source", help="只运行指定来源 ID")
    collect.add_argument("--since-hours", type=_positive_int, default=24, help="只收集指定小时范围内的内容")
    collect.add_argument("--limit", type=_positive_int, default=20, help="每个来源最多处理的条目数")
    collect.add_argument("--dry-run", action="store_true", help="只显示结果，不写 inbox 或去重状态")
    edit = commands.add_parser("edit", help="筛选 inbox 候选并创建人工编辑草稿")
    edit.add_argument("--limit", type=_positive_int, default=10, help="本轮最多选择的候选数")
    edit.add_argument(
        "--select",
        dest="select_news_ids",
        action="append",
        default=[],
        metavar="NEWS_ID",
        help="人工指定入选资讯 ID；可重复指定，报告仍保留全部候选及评分",
    )
    edit.add_argument("--dry-run", action="store_true", help="预览筛选结果，不写报告或草稿")
    publish = commands.add_parser("publish", help="校验编辑草稿并生成本地 Jekyll 文章")
    publish.add_argument("--limit", type=_positive_int, default=5, help="本轮最多生成的文章数")
    publish.add_argument("--dry-run", action="store_true", help="验证并预览，不写文章或发布状态")
    commands.add_parser("health", help="检查来源可访问性和解析情况")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    try:
        if args.command == "collect":
            sources = load_sources()
            if args.source:
                selected = [source for source in sources if source.id == args.source]
                if not selected:
                    print(f"未知来源 ID：{args.source}", file=sys.stderr)
                    return 2
                sources = selected
            result = collect_sources(
                sources,
                since_hours=args.since_hours,
                limit=args.limit,
                dry_run=args.dry_run,
            )
            _print_rows(result["rows"])
            print(f"新条目：{result['new_items']}；dry-run：{'是' if args.dry_run else '否'}")
            return result["exit_code"]

        if args.command == "edit":
            result = run_edit(
                limit=args.limit,
                dry_run=args.dry_run,
                selected_news_ids=set(args.select_news_ids) or None,
            )
            if args.dry_run:
                print(result["report"], end="")
            else:
                print(f"筛选报告：{result['report_path']}")
                print(f"候选 {result['candidate_count']} 条；入选 {result['selected_count']} 条")
                print(f"草稿目录：{result['draft_dir']}")
            print(f"dry-run：{'是' if args.dry_run else '否'}")
            return 0

        if args.command == "publish":
            result = run_publish(limit=args.limit, dry_run=args.dry_run)
            action = "计划生成" if args.dry_run else "已生成"
            print(f"{action} {result['planned_count']} 篇；跳过已发布 {result['skipped_count']} 篇")
            for record in result["records"]:
                print(f"  {record['post_path']} <- {record['source_url']}")
            print(f"dry-run：{'是' if args.dry_run else '否'}")
            return 0

        sources = load_sources()
        result = check_sources(sources)
        _print_rows(result["rows"], health=True)
        return result["exit_code"]
    except (ValueError, OSError) as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
