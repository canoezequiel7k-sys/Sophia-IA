from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from companera.infrastructure.pacific_time import next_pacific_midnight


@dataclass(frozen=True)
class QuotaInfo:
    kind: str
    retry_after: int | None = None


def classify_quota(body_text: str) -> QuotaInfo:
    lower = body_text.lower()
    kind = "unknown"
    if "perday" in lower or "per day" in lower or "daily" in lower:
        kind = "day"
    elif "perminute" in lower or "per minute" in lower:
        kind = "minute"
    elif "token" in lower:
        kind = "tokens"
    retry = None
    match = re.search(r"retryDelay.*?([0-9]+)s", body_text, re.I | re.S)
    if match:
        retry = int(match.group(1))
    return QuotaInfo(kind, retry)


class QuotaState:
    def __init__(self) -> None:
        self._blocks: dict[str, datetime] = {}

    def mark(self, profile_id: str, info: QuotaInfo, now_utc: datetime) -> None:
        if info.kind == "day":
            until = next_pacific_midnight(now_utc)
        else:
            seconds = max(0, min(120, info.retry_after if info.retry_after is not None else 60))
            until = now_utc + timedelta(seconds=seconds)
        self._blocks[profile_id] = until

    def blocked_until(self, profile_id: str, now: datetime) -> datetime | None:
        until = self._blocks.get(profile_id)
        if until and until > now:
            return until
        if until:
            self._blocks.pop(profile_id, None)
        return None
