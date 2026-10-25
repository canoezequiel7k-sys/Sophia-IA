from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Mood(str, Enum):
    CALM = "calm"
    HAPPY = "happy"
    SAD = "sad"
    ANXIOUS = "anxious"
    TIRED = "tired"


class Topic(str, Enum):
    PROGRAMMING = "programación"
    WORK = "trabajo"
    FAMILY = "familia"
    RELATIONSHIPS = "relaciones"
    HEALTH = "salud"
    STUDY = "estudio"
    GENERAL = "general"


@dataclass(frozen=True)
class CheckIn:
    text: str
    mood: Mood
    topic: Topic
    created_at: datetime
    reply: str = ""
