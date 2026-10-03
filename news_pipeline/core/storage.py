from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from news_pipeline.core.dedupe import DedupeIndex
from news_pipeline.core.models import NewsItem
from news_pipeline.core.normalize import normalize_title


class SeenStateError(ValueError):
    pass


class InboxStore:
    def __init__(self, pipeline_root: str | Path) -> None:
        self.pipeline_root = Path(pipeline_root)
        self.inbox_dir = self.pipeline_root / "storage" / "inbox"
        self.seen_path = self.pipeline_root / "state" / "seen.jsonl"

    def load_index(self) -> DedupeIndex:
        index = DedupeIndex()
        if self.seen_path.exists():
            try:
                lines = self.seen_path.read_text(encoding="utf-8").splitlines()
            except OSError as exc:
                raise SeenStateError(f"Could not read {self.seen_path}: {exc}") from exc
            for line_number, line in enumerate(lines, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SeenStateError(f"Invalid JSON in {self.seen_path} at line {line_number}") from exc
                if not isinstance(record, dict) or not record.get("id") or not record.get("canonical_url"):
                    raise SeenStateError(f"Invalid seen record in {self.seen_path} at line {line_number}")
                index.add_record(record)

        if self.inbox_dir.exists():
            for item_path in sorted(self.inbox_dir.glob("*.json")):
                try:
                    record = json.loads(item_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise SeenStateError(f"Invalid inbox item {item_path}: {exc}") from exc
                if not isinstance(record, dict) or not record.get("id") or not record.get("canonical_url"):
                    raise SeenStateError(f"Invalid inbox item {item_path}: required fields are missing")
                index.add_record(record)
        return index

    def save(self, items: list[NewsItem], *, dry_run: bool = False) -> list[NewsItem]:
        index = self.load_index()
        new_items: list[NewsItem] = []
        for item in items:
            if index.add(item):
                new_items.append(item)

        if dry_run or not new_items:
            return new_items

        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.seen_path.parent.mkdir(parents=True, exist_ok=True)
        for item in new_items:
            self._write_json(self.inbox_dir / self._filename(item), item.to_dict())
        self._write_jsonl(self.seen_path, index.records)
        return new_items

    def _filename(self, item: NewsItem) -> str:
        fetched = datetime.fromisoformat(item.fetched_at.replace("Z", "+00:00"))
        local = fetched.astimezone(ZoneInfo("Asia/Shanghai"))
        return f"{local:%Y%m%d-%H%M}-{item.source_id}-{item.id}.json"

    def _write_json(self, path: Path, value: dict) -> None:
        self._atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")

    def _write_jsonl(self, path: Path, records: list[dict]) -> None:
        content = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
        self._atomic_write(path, content)

    def _atomic_write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="\n", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
            ) as temporary_file:
                temporary_file.write(content)
                temporary_path = temporary_file.name
            os.replace(temporary_path, path)
        except OSError:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise
