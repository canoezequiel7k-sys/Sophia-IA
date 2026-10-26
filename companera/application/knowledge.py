from dataclasses import dataclass
from typing import Protocol

from companera.application.ports import Clock, MemoryRepository
from companera.domain.models import CheckIn, Mood, Topic


@dataclass(frozen=True)
class KnowledgeEntry:
    title: str
    summary: str
    content: str
    source: str


class KnowledgeBase(Protocol):
    def search(self, query: str, limit: int = 5) -> list[KnowledgeEntry]: ...


class SearchKnowledgeUseCase:
    def __init__(self, knowledge_base: KnowledgeBase):
        self._knowledge_base = knowledge_base

    def execute(self, query: str) -> list[KnowledgeEntry]:
        return self._knowledge_base.search(query)


class RecordInteractionUseCase:
    def __init__(self, memory: MemoryRepository, clock: Clock):
        self._memory = memory
        self._clock = clock

    def execute(self, user_text: str, assistant_text: str) -> None:
        self._memory.save(
            CheckIn(
                text=user_text,
                mood=Mood.CALM,
                topic=Topic.PROGRAMMING,
                created_at=self._clock.now(),
                reply=assistant_text,
            )
        )
