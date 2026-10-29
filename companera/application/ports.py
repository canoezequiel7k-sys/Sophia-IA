from datetime import datetime
from typing import Protocol

from companera.domain.models import CheckIn


class MemoryRepository(Protocol):
    """Contrato que cualquier almacenamiento de recuerdos debe cumplir."""

    def latest(self) -> CheckIn | None: ...
    def history(self) -> list[CheckIn]: ...
    def save(self, check_in: CheckIn) -> None: ...
    def clear(self) -> None: ...


class Clock(Protocol):
    """Permite obtener la hora sin acoplar los casos de uso al sistema."""

    def now(self) -> datetime: ...
