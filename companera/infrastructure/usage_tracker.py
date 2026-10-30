from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from companera.domain.models import TokenUsage
from companera.infrastructure.pacific_time import pacific_day_key

logger = logging.getLogger("sophia.usage")


@dataclass(frozen=True)
class DayUsage:
    requests: int = 0
    prompt: int = 0
    completion: int = 0
    total: int = 0
    last_total: int = 0


class UsageTracker:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, object] = self._load()

    def _load(self) -> dict[str, object]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except (json.JSONDecodeError, OSError):
            logger.warning("data/uso.json está dañado; se usa registro vacío")
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp: Path | None = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False, suffix=".json") as handle:
                tmp = Path(handle.name)
                json.dump(self.data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            tmp.replace(self.path)
        finally:
            if tmp is not None and tmp.exists():
                tmp.unlink(missing_ok=True)

    def record(self, profile_id: str, usage: TokenUsage | None, now_utc: datetime) -> None:
        kind_gemini = profile_id.startswith("gemini")
        day = pacific_day_key(now_utc) if kind_gemini else now_utc.astimezone().strftime("%Y-%m-%d")
        root = self.data.setdefault(day, {})
        if not isinstance(root, dict):
            root = {}
            self.data[day] = root
        row = root.setdefault(profile_id, {"requests": 0, "prompt": 0, "completion": 0, "total": 0, "last_total": 0})
        if not isinstance(row, dict):
            row = {"requests": 0, "prompt": 0, "completion": 0, "total": 0, "last_total": 0}
            root[profile_id] = row
        u = usage or TokenUsage()
        row["requests"] = int(row.get("requests", 0)) + 1
        row["prompt"] = int(row.get("prompt", 0)) + max(0, u.prompt)
        row["completion"] = int(row.get("completion", 0)) + max(0, u.completion)
        row["total"] = int(row.get("total", 0)) + max(0, u.total)
        row["last_total"] = max(0, u.total)
        # Conserva solo 30 días
        for old in sorted(str(x) for x in self.data.keys())[:-30]:
            self.data.pop(old, None)
        self._save()

    def today(self, profile_id: str, now_utc: datetime) -> DayUsage:
        kind_gemini = profile_id.startswith("gemini")
        day = pacific_day_key(now_utc) if kind_gemini else now_utc.astimezone().strftime("%Y-%m-%d")
        root = self.data.get(day, {}) if isinstance(self.data, dict) else {}
        row = root.get(profile_id, {}) if isinstance(root, dict) else {}
        if not isinstance(row, dict):
            return DayUsage()
        return DayUsage(
            int(row.get("requests", 0)), int(row.get("prompt", 0)),
            int(row.get("completion", 0)), int(row.get("total", 0)),
            int(row.get("last_total", 0)),
        )


def format_tokens(value: int) -> str:
    value = max(0, int(value))
    if value < 1000:
        return str(value)
    if value < 1_000_000:
        return f"{value / 1000:.1f}".replace(".", ",") + "k"
    return f"{value / 1_000_000:.1f}".replace(".", ",") + "M"
