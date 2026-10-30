from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

VALID_EXPRESSIONS = frozenset({"calm", "laugh", "smug", "look", "aside", "wide", "many"})

@dataclass(frozen=True)
class Reply:
    """Resultado tipado de una generación de Sophia."""
    text: str
    expression: str = "calm"
    ok: bool = True
    error_code: str | None = None
    mood: object | None = None
    topic: object | None = None
    facts: tuple[str, ...] = ()


class Mood(str, Enum):
    """Estado de ánimo que Sophia percibe en la conversación."""
    CALM = "calm"
    HAPPY = "happy"
    SAD = "sad"
    ANXIOUS = "anxious"
    TIRED = "tired"


class Topic(str, Enum):
    """Categoría general del intercambio para organizar la memoria."""
    GENERAL = "general"
    PERSONAL = "personal"
    TECHNICAL = "technical"
    CREATIVE = "creative"


@dataclass(frozen=True)
class CheckIn:
    """Un intercambio guardado para que Sophia recuerde la conversación."""
    text: str
    mood: Mood
    topic: Topic
    created_at: datetime
    reply: str = ""
