from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from news_pipeline.core.models import NewsItem, SourceConfig
from news_pipeline.core.fetch import HttpFetcher


class BaseCollector(ABC):
    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    @abstractmethod
    def collect(
        self,
        source: SourceConfig,
        *,
        since_hours: int,
        limit: int,
        fetched_at: datetime | None = None,
    ) -> list[NewsItem]:
        raise NotImplementedError
