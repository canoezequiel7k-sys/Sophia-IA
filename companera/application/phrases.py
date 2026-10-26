from companera.domain.models import Mood, Topic


RESPONSES = {
    # Frases breves según el ánimo reconocido.
    Mood.HAPPY: "Qué lindo leerte así.",
    Mood.SAD: "Siento que estés pasando por algo difícil. Gracias por contármelo.",
    Mood.ANXIOUS: "Suena a que tenés muchas cosas en la cabeza. Podemos ir de a poco.",
    Mood.TIRED: "Parece que necesitás un respiro. Está bien tomarse las cosas con calma.",
    Mood.CALM: "Gracias por compartirlo conmigo.",
}
MOOD_LABELS = {
    # Nombres fáciles de leer para mostrar el ánimo en la terminal.
    Mood.CALM: "en calma",
    Mood.HAPPY: "feliz",
    Mood.SAD: "triste",
    Mood.ANXIOUS: "ansioso/a",
    Mood.TIRED: "cansado/a",
}
QUESTIONS = {
    # Preguntas de seguimiento para que la charla pueda continuar.
    Topic.PROGRAMMING: (
        "¿Qué esperabas que hiciera el código y qué ocurrió? "
        "Si hay un error, pegá el mensaje completo."
    ),
    Topic.WORK: "¿Qué fue lo que más te afectó del trabajo hoy?",
    Topic.FAMILY: "¿Qué pasó con tu familia?",
    Topic.RELATIONSHIPS: "¿Cómo te hizo sentir esa situación?",
    Topic.HEALTH: "¿Desde cuándo te sentís así?",
    Topic.STUDY: "¿Qué parte del estudio o del examen te preocupa más?",
    Topic.GENERAL: "¿Qué pasó para que te sintieras así?",
}


def reply_for(mood: Mood, topic: Topic, previous_mood: Mood | None) -> str:
    """Combina ánimo, tema y recuerdo previo en una respuesta."""
    if topic == Topic.PROGRAMMING:
        return f"Te ayudo a revisarlo paso a paso. {QUESTIONS[topic]}"
    response = RESPONSES[mood]
    if previous_mood is not None:
        if previous_mood != mood:
            response += (
                f" La última vez te sentías {MOOD_LABELS[previous_mood]};"
                f" hoy te noto {MOOD_LABELS[mood]}."
            )
        else:
            response += " Me acuerdo de que la última vez también te sentías así."
    return f"{response} {QUESTIONS[topic]}"
