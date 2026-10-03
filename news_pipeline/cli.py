from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
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
from news_pipeline.core.models import SourceConfig
from news_pipeline.core.storage import InboxStore


LOGGER = logging.getLogger("news_pipeline")
PIPELINE_ROOT = Path(__file__).resolve().parent
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
    parser = argparse.ArgumentParser(description="PERSONAL-BLOG 本地 AI 资讯采集器")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="采集最近新增的资讯到本地 inbox")
    collect.add_argument("--source", help="只运行指定来源 ID")
    collect.add_argument("--since-hours", type=_positive_int, default=24, help="只收集指定小时范围内的内容")
    collect.add_argument("--limit", type=_positive_int, default=20, help="每个来源最多处理的条目数")
    collect.add_argument("--dry-run", action="store_true", help="只显示结果，不写 inbox 或去重状态")
    commands.add_parser("health", help="检查来源可访问性和解析情况")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    try:
        sources = load_sources()
        if args.command == "collect":
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

        result = check_sources(sources)
        _print_rows(result["rows"], health=True)
        return result["exit_code"]
    except (ValueError, OSError) as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
