from datetime import datetime
from typing import Protocol

from companera.domain.models import CheckIn, Mood, Topic


class MemoryRepository(Protocol):
    """Lo que cualquier almacenamiento de recuerdos debe ofrecer."""
    def latest(self) -> CheckIn | None: ...

    def history(self) -> list[CheckIn]: ...

    def save(self, check_in: CheckIn) -> None: ...

    def clear(self) -> None: ...


class TextAnalyzer(Protocol):
    """Permite cambiar el analizador sin modificar la conversación."""
    def analyze(self, text: str) -> tuple[Mood, Topic]: ...


class Clock(Protocol):
    """Permite obtener la hora sin acoplar los casos de uso al sistema."""
    def now(self) -> datetime: ...
