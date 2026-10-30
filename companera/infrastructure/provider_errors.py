from __future__ import annotations
from dataclasses import dataclass
from companera.domain.models import TokenUsage


@dataclass(frozen=True)
class RawCompletion:
    text: str
    usage: TokenUsage
    finish_reason: str = ""


class ProviderError(Exception):
    def __init__(self, code: str, retry_after: int | None = None, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after
        self.detail = detail
