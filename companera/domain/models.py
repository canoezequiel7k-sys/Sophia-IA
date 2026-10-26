from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Mood(str, Enum):
    """Ánimos que el analizador local sabe reconocer."""
    CALM = "calm"
    HAPPY = "happy"
    SAD = "sad"
    ANXIOUS = "anxious"
    TIRED = "tired"


class Topic(str, Enum):
    """Temas que ayudan a elegir la respuesta adecuada."""
    PROGRAMMING = "programación"
    WORK = "trabajo"
    FAMILY = "familia"
    RELATIONSHIPS = "relaciones"
    HEALTH = "salud"
    STUDY = "estudio"
    GENERAL = "general"


@dataclass(frozen=True)
class CheckIn:
    """Una conversación guardada para poder recordarla más adelante."""
    text: str
    mood: Mood
    topic: Topic
    created_at: datetime
    reply: str = ""
