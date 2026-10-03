from __future__ import annotations


CATEGORIES = (
    "模型发布",
    "产品更新",
    "研究进展",
    "开源项目",
    "AI 工具",
    "AI 基础设施",
    "安全与治理",
    "行业动态",
)


def normalize_tags(tags: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Trim tags and remove case-insensitive duplicates while preserving order."""
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        value = tag.strip()
        key = value.casefold()
        if value and key not in seen:
            normalized.append(value)
            seen.add(key)
    return tuple(normalized)
