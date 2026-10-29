from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
