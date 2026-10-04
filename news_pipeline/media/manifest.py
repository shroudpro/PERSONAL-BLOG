from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class CoverManifest:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.records: list[dict[str, Any]] = []
        if self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid cover manifest {self.path}: {exc}") from exc
            if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(payload.get("covers"), list):
                raise ValueError(f"Invalid cover manifest schema: {self.path}")
            self.records = payload["covers"]

    def by_slug(self, post_slug: str) -> dict[str, Any] | None:
        return next((record for record in self.records if record.get("post_slug") == post_slug), None)

    def by_sha256(self, sha256: str) -> dict[str, Any] | None:
        return next((record for record in self.records if record.get("sha256") == sha256), None)

    def add(self, **record: Any) -> dict[str, Any]:
        duplicate = self.by_sha256(record["sha256"])
        if duplicate:
            record["local_path"] = duplicate["local_path"]
        self.records = [existing for existing in self.records if existing.get("post_slug") != record["post_slug"]]
        self.records.append(record)
        self.records.sort(key=lambda entry: entry["post_slug"])
        return record

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"schema_version": 1, "covers": self.records}, ensure_ascii=False, indent=2) + "\n"
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="\n", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
            ) as temporary_file:
                temporary_file.write(payload)
                temporary_path = temporary_file.name
            os.replace(temporary_path, self.path)
        except OSError:
            if temporary_path and Path(temporary_path).exists():
                Path(temporary_path).unlink()
            raise
