import re
import unicodedata

from companera.domain.models import Mood, Topic


MOOD_WORDS = {
    Mood.HAPPY: {"feliz", "contento", "contenta", "alegre", "genial", "bien", "emocionado", "emocionada"},
    Mood.SAD: {"triste", "mal", "solo", "sola", "llorar", "deprimido", "deprimida"},
    Mood.ANXIOUS: {"ansioso", "ansiosa", "nervioso", "nerviosa", "preocupado", "preocupada", "estresado", "estresada", "miedo"},
    Mood.TIRED: {"cansado", "cansada", "agotado", "agotada", "sueño", "dormir"},
}
TOPIC_WORDS = {
    Topic.WORK: {"trabajo", "jefe", "oficina", "compañero", "compañera", "empleo"},
    Topic.FAMILY: {"familia", "madre", "padre", "mamá", "papá", "hermano", "hermana"},
    Topic.RELATIONSHIPS: {"pareja", "amigo", "amiga", "relación", "novio", "novia"},
    Topic.HEALTH: {"salud", "médico", "dolor", "enfermo", "enferma"},
    Topic.STUDY: {"estudio", "estudiar", "examen", "escuela", "universidad", "clase"},
}


def _words(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFD", text.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return set(re.findall(r"[a-z0-9]+", normalized))


def _normalized_words(groups: dict) -> dict:
    return {key: {word for phrase in values for word in _words(phrase)} for key, values in groups.items()}


class KeywordTextAnalyzer:
    def analyze(self, text: str) -> tuple[Mood, Topic]:
        words = _words(text)
        moods = _normalized_words(MOOD_WORDS)
        topics = _normalized_words(TOPIC_WORDS)
        mood = max(moods, key=lambda item: len(words & moods[item]), default=Mood.CALM)
        if not words.intersection(moods.get(mood, set())):
            mood = Mood.CALM
        topic = max(topics, key=lambda item: len(words & topics[item]), default=Topic.GENERAL)
        if not words.intersection(topics.get(topic, set())):
            topic = Topic.GENERAL
        return mood, topic
