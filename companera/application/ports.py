from datetime import datetime
from typing import Protocol

from companera.domain.models import CheckIn, Mood, Topic


class MemoryRepository(Protocol):
    def latest(self) -> CheckIn | None: ...

    def history(self) -> list[CheckIn]: ...

    def save(self, check_in: CheckIn) -> None: ...

    def clear(self) -> None: ...


class TextAnalyzer(Protocol):
    def analyze(self, text: str) -> tuple[Mood, Topic]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
