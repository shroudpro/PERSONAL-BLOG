from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from news_pipeline.core.models import NewsItem


@dataclass(frozen=True)
class EditorArticle:
    news_id: str
    source_id: str
    source_name: str
    title: str
    slug: str
    date: str
    summary: str
    category: str
    tags: tuple[str, ...]
    source_url: str
    source_published_at: str | None
    body_markdown: str
    image: str | None = None

    @classmethod
    def from_news_item(cls, item: NewsItem, *, date: str, slug: str) -> EditorArticle:
        return cls(
            news_id=item.id,
            source_id=item.source_id,
            source_name=item.source_name,
            title=item.title,
            slug=slug,
            date=date,
            summary="",
            category="",
            tags=(),
            source_url=item.canonical_url,
            source_published_at=item.published_at,
            body_markdown="",
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EditorArticle:
        required = {
            "news_id",
            "source_id",
            "source_name",
            "title",
            "slug",
            "date",
            "summary",
            "category",
            "tags",
            "source_url",
            "source_published_at",
            "body_markdown",
        }
        missing = sorted(required - value.keys())
        if missing:
            raise ValueError(f"Editor article is missing fields: {', '.join(missing)}")
        for field_name in required - {"tags", "source_published_at"}:
            if not isinstance(value[field_name], str):
                raise ValueError(f"Editor article field {field_name} must be a string")
        tags = value["tags"]
        if not isinstance(tags, (list, tuple)) or any(not isinstance(tag, str) for tag in tags):
            raise ValueError("Editor article field tags must be a list of strings")
        source_published_at = value["source_published_at"]
        if source_published_at is not None and not isinstance(source_published_at, str):
            raise ValueError("Editor article field source_published_at must be a string or null")
        image = value.get("image")
        if image is not None and not isinstance(image, str):
            raise ValueError("Editor article field image must be a string or null")

        return cls(
            news_id=value["news_id"],
            source_id=value["source_id"],
            source_name=value["source_name"],
            title=value["title"],
            slug=value["slug"],
            date=value["date"],
            summary=value["summary"],
            category=value["category"],
            tags=tuple(tags),
            source_url=value["source_url"],
            source_published_at=source_published_at,
            body_markdown=value["body_markdown"],
            image=image,
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["tags"] = list(self.tags)
        return value
