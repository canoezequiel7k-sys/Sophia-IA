from __future__ import annotations

import logging

from companera.application.ports import Clock, LanguageModel, MemoryRepository
from companera.domain.models import CheckIn, Mood, Reply, Topic

logger = logging.getLogger("sophia.chat")


class ChatService:
    """Orquesta una conversación sin conocer Tkinter ni pygame."""

    def __init__(self, memory: MemoryRepository, clock: Clock, model: LanguageModel) -> None:
        self._memory = memory
        self._clock = clock
        self._model = model

    def send(self, user_text: str) -> Reply:
        history = self._memory.history()
        reply = self._model.generate_reply(user_text, history=history)
        if not reply.ok:
            return reply
        try:
            self._memory.save(CheckIn(
                text=user_text,
                mood=reply.mood or Mood.CALM,
                topic=reply.topic or Topic.GENERAL,
                created_at=self._clock.now(),
                reply=reply.text,
            ))
        except Exception:
            logger.exception("No se pudo persistir el intercambio")
        return reply
