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
    Topic.PROGRAMMING: {
        "python", "codigo", "programar", "programacion", "error", "traceback",
        "funcion", "variable", "bug", "script", "clase", "prueba",
    },
    Topic.WORK: {"trabajo", "jefe", "oficina", "compañero", "compañera", "empleo"},
    Topic.FAMILY: {"familia", "madre", "padre", "mamá", "papá", "hermano", "hermana"},
    Topic.RELATIONSHIPS: {"pareja", "amigo", "amiga", "relación", "novio", "novia"},
    Topic.HEALTH: {"salud", "médico", "dolor", "enfermo", "enferma"},
    Topic.STUDY: {"estudio", "estudiar", "examen", "escuela", "universidad", "clase"},
}


def _tokens(text: str) -> list[str]:
    """Separa el mensaje en palabras y quita tildes para comparar."""
    normalized = unicodedata.normalize("NFD", text.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.findall(r"[a-z0-9]+", normalized)


def _words(text: str) -> set[str]:
    """Devuelve las palabras únicas del texto."""
    return set(_tokens(text))


def _normalized_words(groups: dict) -> dict:
    """Prepara las listas de palabras que usa el analizador."""
    return {key: {word for phrase in values for word in _words(phrase)} for key, values in groups.items()}


class KeywordTextAnalyzer:
    """Detecta ánimo y tema con reglas locales, sin enviar texto a internet."""
    def analyze(self, text: str) -> tuple[Mood, Topic]:
        """Busca coincidencias y devuelve el ánimo y tema más probables."""
        tokens = _tokens(text)
        words = set(tokens)
        moods = _normalized_words(MOOD_WORDS)
        topics = _normalized_words(TOPIC_WORDS)
        negations = {"no", "nunca", "tampoco", "jamas"}
        mood_scores = {
            mood: sum(
                1
                for index, token in enumerate(tokens)
                if token in mood_words
                and not negations.intersection(tokens[max(0, index - 3):index])
            )
            for mood, mood_words in moods.items()
        }
        mood = max(mood_scores, key=mood_scores.get, default=Mood.CALM)
        if mood_scores.get(mood, 0) == 0:
            mood = Mood.CALM
        topic = max(topics, key=lambda item: len(words & topics[item]), default=Topic.GENERAL)
        if not words.intersection(topics.get(topic, set())):
            topic = Topic.GENERAL
        return mood, topic
