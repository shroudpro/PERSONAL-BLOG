from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from news_pipeline.core.models import NewsItem
from news_pipeline.core.normalize import normalize_title, normalize_url, parse_datetime_value


_STOP_WORDS = {"the", "and", "for", "with", "from", "into", "our", "their", "this", "that"}
_AI_TERMS = {
    "ai",
    "agent",
    "agents",
    "artificial intelligence",
    "biology",
    "computer-use",
    "foundation model",
    "generative",
    "inference",
    "llm",
    "machine learning",
    "model",
    "models",
    "neural",
    "protein",
    "robotics",
    "synthetic biology",
    "token",
    "watermark",
}
_VALUE_TERMS = {
    "agent",
    "api",
    "benchmark",
    "biology",
    "computer-use",
    "developer",
    "engineering",
    "infrastructure",
    "model",
    "open-source",
    "protein",
    "research",
    "safety",
    "scientific",
    "security",
    "tool",
    "training",
}
_INCREMENT_TERMS = {
    "announce",
    "announcing",
    "first",
    "introduce",
    "introducing",
    "launch",
    "launches",
    "new",
    "open-sourcing",
    "prototype",
    "release",
    "research",
    "unveils",
    "watermarking",
}
_LOW_PRIORITY_TERMS = {
    "career fair",
    "event",
    "hiring",
    "job opening",
    "register now",
    "trailer",
    "webinar",
}
_SHANGHAI = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class SelectionDecision:
    item: NewsItem
    selected: bool
    score: int
    dimensions: dict[str, int]
    reasons: tuple[str, ...]
    duplicate_of: str | None = None


def _words(value: str) -> set[str]:
    return {
        word.casefold()
        for word in re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", value.casefold())
        if len(word) > 2 and word not in _STOP_WORDS
    }


def _contains_term(text: str, term: str) -> bool:
    expression = rf"(?<![a-z0-9]){re.escape(term.casefold())}(?![a-z0-9])"
    return re.search(expression, text.casefold()) is not None


def _source_specificity(item: NewsItem) -> int:
    """Prefer a publisher's own specialist domain over a generic cross-post."""
    host_labels = set(urlsplit(item.canonical_url).hostname.casefold().split("."))
    source_labels = set(re.findall(r"[a-z0-9]+", item.source_id.casefold()))
    return len(host_labels & source_labels)


def _score_item(item: NewsItem, now: datetime) -> tuple[dict[str, int], tuple[str, ...]]:
    text = " ".join(
        (item.title, item.summary_raw or "", item.content_text or "")
    )
    lower_text = text.casefold()
    source_authority = 5 if item.source_type in {"official", "research"} else 1

    published = parse_datetime_value(item.published_at)
    age_days = (now.astimezone(timezone.utc) - published).total_seconds() / 86400 if published else None
    if age_days is None:
        timeliness = 0
    elif age_days < -1:
        timeliness = 1
    elif age_days <= 7:
        timeliness = 5
    elif age_days <= 30:
        timeliness = 4
    elif age_days <= 90:
        timeliness = 2
    else:
        timeliness = 0

    relevance_hits = sum(_contains_term(lower_text, term) for term in _AI_TERMS)
    ai_relevance = 5 if relevance_hits >= 3 else 4 if relevance_hits >= 2 else 3 if relevance_hits else 1

    increment_hits = sum(_contains_term(lower_text, term) for term in _INCREMENT_TERMS)
    summary_length = len(item.summary_raw or item.content_text or "")
    information_gain = 5 if increment_hits >= 3 or summary_length >= 240 else 4 if increment_hits else 2 if summary_length >= 80 else 1

    reader_hits = sum(_contains_term(lower_text, term) for term in _VALUE_TERMS)
    reader_value = 5 if reader_hits >= 4 else 4 if reader_hits >= 2 else 3 if reader_hits else 1
    duplicate_score = 5

    low_priority = any(_contains_term(lower_text, term) for term in _LOW_PRIORITY_TERMS)
    dimensions = {
        "来源权威性": source_authority,
        "时效性": timeliness,
        "AI 相关性": ai_relevance,
        "信息增量": information_gain,
        "技术读者价值": reader_value,
        "去重": duplicate_score,
    }
    score = sum(dimensions.values()) - (6 if low_priority else 0)
    reasons = [
        f"权威来源 {source_authority}/5",
        "发布日期缺失" if published is None else ("近 7 天" if timeliness == 5 else "超过 7 天"),
        f"AI 相关性 {ai_relevance}/5",
        f"信息增量 {information_gain}/5",
        f"技术读者价值 {reader_value}/5",
    ]
    if low_priority:
        reasons.append("活动或营销信息，降低优先级")
    return dimensions, tuple(reasons)


def _is_duplicate(left: NewsItem, right: NewsItem) -> bool:
    try:
        if normalize_url(left.canonical_url) == normalize_url(right.canonical_url):
            return True
    except ValueError:
        pass
    if normalize_title(left.title) == normalize_title(right.title):
        return True
    left_words = _words(left.title)
    right_words = _words(right.title)
    shared = left_words & right_words
    union = left_words | right_words
    return len(shared) >= 3 and len(shared) / len(union) >= 0.55 if union else False


def select_candidates(
    items: list[NewsItem],
    *,
    limit: int,
    now: datetime | None = None,
    published_records: list[dict] | None = None,
    existing_draft_ids: set[str] | None = None,
    selected_news_ids: set[str] | None = None,
) -> list[SelectionDecision]:
    if limit < 1:
        raise ValueError("limit must be positive")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    published_records = published_records or []
    existing_draft_ids = existing_draft_ids or set()
    selected_news_ids = selected_news_ids or set()
    if len(selected_news_ids) > limit:
        raise ValueError("the number of manually selected news IDs cannot exceed limit")
    known_ids = {item.id for item in items}
    unknown_ids = selected_news_ids - known_ids
    if unknown_ids:
        raise ValueError(f"unknown manually selected news IDs: {', '.join(sorted(unknown_ids))}")
    published_ids = {str(record.get("news_id", "")) for record in published_records}
    published_urls = set()
    for record in published_records:
        url = record.get("source_url")
        if isinstance(url, str):
            try:
                published_urls.add(normalize_url(url))
            except ValueError:
                continue

    def already_published(item: NewsItem) -> bool:
        if item.id in published_ids:
            return True
        try:
            return normalize_url(item.canonical_url) in published_urls
        except ValueError:
            return False

    scored = []
    for item in items:
        dimensions, reasons = _score_item(item, now)
        scored.append((item, dimensions, reasons, sum(dimensions.values())))
    scored.sort(
        key=lambda row: (
            row[0].id in existing_draft_ids,
            row[3],
            _source_specificity(row[0]),
            row[0].published_at or "",
            row[0].id,
        ),
        reverse=True,
    )

    winners: list[tuple[NewsItem, dict[str, int], tuple[str, ...], int]] = []
    duplicates: dict[str, str] = {}
    for row in scored:
        item = row[0]
        for winner_index, winner in enumerate(winners):
            if _is_duplicate(item, winner[0]):
                if _source_specificity(item) > _source_specificity(winner[0]):
                    replaced_id = winner[0].id
                    winners[winner_index] = row
                    duplicates[replaced_id] = item.id
                    for duplicate_id, winner_id in tuple(duplicates.items()):
                        if winner_id == replaced_id:
                            duplicates[duplicate_id] = item.id
                else:
                    duplicates[item.id] = winner[0].id
                break
        else:
            winners.append(row)

    winner_ids = {row[0].id for row in winners}
    manual_ids = {duplicates.get(news_id, news_id) for news_id in selected_news_ids}
    winner_by_id = {row[0].id: row[0] for row in winners}
    published_manual_ids = {
        news_id for news_id in manual_ids if news_id not in winner_by_id or already_published(winner_by_id[news_id])
    }
    if published_manual_ids:
        raise ValueError(f"manually selected news IDs are already published: {', '.join(sorted(published_manual_ids))}")
    manual_ids.intersection_update(winner_ids)
    pending = [row for row in winners if row[0].id in existing_draft_ids and not already_published(row[0])]
    new_candidates = [row for row in winners if row[0].id not in existing_draft_ids and not already_published(row[0])]
    selected_ids = set(manual_ids)
    for row in pending:
        if row[0].id not in selected_ids and len(selected_ids) < limit:
            selected_ids.add(row[0].id)
    remaining = max(0, limit - len(selected_ids))
    for row in new_candidates:
        if remaining <= 0:
            continue
        selected_ids.add(row[0].id)
        remaining -= 1

    decisions: list[SelectionDecision] = []
    for item, dimensions, score_reasons, score in scored:
        reasons = list(score_reasons)
        duplicate_of = duplicates.get(item.id)
        if duplicate_of:
            reasons.append(f"与候选 {duplicate_of} 内容重复，保留更具来源代表性的页面")
        elif already_published(item):
            reasons.append("该资讯已发布，跳过")
        selected = item.id in selected_ids and not duplicate_of and not already_published(item)
        if selected:
            reasons.append(
                "人工指定入选，已优先进行原文核验和主题覆盖"
                if item.id in manual_ids
                else "进入本轮待编辑清单"
            )
        elif not duplicate_of and item.id not in published_ids:
            published = parse_datetime_value(item.published_at)
            if published is None:
                reasons.append("缺少发布日期，需原文核验后再选")
            elif (now.astimezone(timezone.utc) - published).days > 30:
                reasons.append("时效不足")
            else:
                reasons.append("本轮排序未进入数量上限")
        decisions.append(
            SelectionDecision(
                item=item,
                selected=selected,
                score=score,
                dimensions=dimensions,
                reasons=tuple(reasons),
                duplicate_of=duplicate_of,
            )
        )
    return decisions


def render_selection_report(decisions: list[SelectionDecision], *, now: datetime) -> str:
    selected_count = sum(decision.selected for decision in decisions)
    lines = [
        "# AI 资讯编辑筛选报告",
        "",
        f"- 生成时间（Asia/Shanghai）：{now.astimezone(_SHANGHAI).isoformat(timespec='minutes')}",
        f"- 候选：{len(decisions)} 条；入选：{selected_count} 条。",
        "- 评分维度：来源权威性、时效性、AI 相关性、信息增量、技术读者价值、重复度。",
        "- 选择结果是待人工核验的候选，不代表文章已审核或发布。",
        "",
        "| 结果 | 来源 | 原始标题 | URL | 理由 |",
        "|---|---|---|---|---|",
    ]
    for decision in decisions:
        label = "选择" if decision.selected else "放弃"
        title = decision.item.title.replace("|", "\\|").replace("\n", " ")
        reason = "；".join(decision.reasons).replace("|", "\\|")
        lines.append(
            f"| {label}（{decision.score} 分） | {decision.item.source_name} | {title} | "
            f"[{decision.item.canonical_url}]({decision.item.canonical_url}) | {reason} |"
        )
    lines.append("")
    return "\n".join(lines)
