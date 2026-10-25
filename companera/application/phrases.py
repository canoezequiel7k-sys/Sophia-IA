from companera.domain.models import Mood, Topic


RESPONSES = {
    Mood.HAPPY: "Qué lindo leerte así.",
    Mood.SAD: "Siento que estés pasando por algo difícil. Gracias por contármelo.",
    Mood.ANXIOUS: "Suena a que tenés muchas cosas en la cabeza. Podemos ir de a poco.",
    Mood.TIRED: "Parece que necesitás un respiro. Está bien tomarse las cosas con calma.",
    Mood.CALM: "Gracias por compartirlo conmigo.",
}
MOOD_LABELS = {
    Mood.CALM: "en calma",
    Mood.HAPPY: "feliz",
    Mood.SAD: "triste",
    Mood.ANXIOUS: "ansioso/a",
    Mood.TIRED: "cansado/a",
}


def reply_for(mood: Mood, topic: Topic, previous_mood: Mood | None) -> str:
    response = RESPONSES[mood]
    if previous_mood is not None:
        if previous_mood != mood:
            response += (
                f" La última vez te sentías {MOOD_LABELS[previous_mood]};"
                f" hoy te noto {MOOD_LABELS[mood]}."
            )
        else:
            response += " Me acuerdo de que la última vez también te sentías así."
    if topic != Topic.GENERAL:
        response += f" ¿Querés contarme un poco más sobre {topic.value}?"
    else:
        response += " ¿Querés contarme un poco más?"
    return response
