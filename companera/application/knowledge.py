from dataclasses import dataclass
from typing import Protocol

from companera.application.ports import Clock, MemoryRepository
from companera.domain.models import CheckIn, Mood, Topic


@dataclass(frozen=True)
class KnowledgeEntry:
    """Una sección de apuntes con su resumen y archivo de origen."""

    title: str
    summary: str
    content: str
    source: str


class KnowledgeBase(Protocol):
    """Contrato para buscar apuntes sin depender del formato de almacenamiento."""

    def search(self, query: str, limit: int = 5) -> list[KnowledgeEntry]: ...


class SearchKnowledgeUseCase:
    """Caso de uso que busca conceptos en la base de conocimiento."""

    def __init__(self, knowledge_base: KnowledgeBase):
        self._knowledge_base = knowledge_base

    def execute(self, query: str) -> list[KnowledgeEntry]:
        """Devuelve las entradas que coinciden con la consulta."""
        return self._knowledge_base.search(query)


class RecordInteractionUseCase:
    """Guarda las consultas de apuntes usando el puerto de memoria."""

    def __init__(self, memory: MemoryRepository, clock: Clock):
        self._memory = memory
        self._clock = clock

    def execute(self, user_text: str, assistant_text: str) -> None:
        """Registra la pregunta y la respuesta como un recuerdo."""
        self._memory.save(
            CheckIn(
                text=user_text,
                mood=Mood.CALM,
                topic=Topic.PROGRAMMING,
                created_at=self._clock.now(),
                reply=assistant_text,
            )
        )
