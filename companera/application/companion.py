from dataclasses import dataclass

from companera.application.phrases import reply_for
from companera.application.ports import Clock, MemoryRepository, TextAnalyzer
from companera.domain.models import CheckIn, Mood, Topic


@dataclass(frozen=True)
class CompanionReply:
    """Respuesta y datos que la terminal necesita mostrar."""

    text: str
    user_mood: str
    topic: Topic


class CheckInUseCase:
    """Analiza un mensaje personal, responde y recuerda el intercambio."""

    def __init__(self, memory: MemoryRepository, analyzer: TextAnalyzer, clock: Clock):
        self._memory = memory
        self._analyzer = analyzer
        self._clock = clock

    def respond(self, text: str) -> CompanionReply:
        """Prepara la respuesta usando el ánimo actual y el recuerdo anterior."""
        text = text.strip()
        if not text:
            raise ValueError("La respuesta no puede estar vacía.")
        previous = self._memory.latest()
        mood, topic = self._analyzer.analyze(text)
        reply = reply_for(mood, topic, previous.mood if previous else None)
        self._memory.save(CheckIn(text, mood, topic, self._clock.now(), reply))
        return CompanionReply(
            text=reply,
            user_mood=mood.value,
            topic=topic,
        )
