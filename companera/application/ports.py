from datetime import datetime
from typing import Protocol

from companera.domain.models import CheckIn, Reply


class MemoryRepository(Protocol):
    """Contrato que cualquier almacenamiento de recuerdos debe cumplir."""

    def latest(self) -> CheckIn | None: ...
    def history(self) -> list[CheckIn]: ...
    def save(self, check_in: CheckIn) -> None: ...
    def clear(self) -> None: ...


class Clock(Protocol):
    """Permite obtener la hora sin acoplar los casos de uso al sistema."""

    def now(self) -> datetime: ...


class LanguageModel(Protocol):
    def generate_reply(self, user_message: str, history: list[CheckIn] | None = None) -> Reply: ...
    def generate_screen_reply(self, user_message: str, image_b64: str) -> Reply: ...


class Speaker(Protocol):
    def speak(self, text: str) -> None: ...
    def stop(self) -> None: ...
    def is_speaking(self) -> bool: ...


class SoundPlayer(Protocol):
    def play(self, name: str) -> None: ...
    def stop(self) -> None: ...


class NullSpeaker:
    def speak(self, text: str) -> None:
        return
    def stop(self) -> None:
        return
    def is_speaking(self) -> bool:
        return False


class NullSoundPlayer:
    def play(self, name: str) -> None:
        return
    def stop(self) -> None:
        return
