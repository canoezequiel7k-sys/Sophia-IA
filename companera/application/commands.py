from __future__ import annotations

COMMANDS = ("/ayuda", "/mute", "/callate", "/perfil", "/olvidar", "/limpiar")


def handle_command(message: str, memory_clear: object | None = None) -> str | None:
    """Interpreta comandos locales; devuelve None si el texto debe ir a Gemini."""
    stripped = message.strip()
    if not stripped.startswith("/"):
        return None
    command = stripped.split(maxsplit=1)[0].lower()
    if command == "/ayuda":
        return "Comandos disponibles: " + ", ".join(COMMANDS)
    if command == "/mute":
        return "Comando mute local recibido."
    if command == "/callate":
        return "Ya no voy a hablar hasta que me lo vuelvas a pedir."
    if command == "/perfil":
        return "Perfil local disponible; todavía no hay datos configurados."
    if command == "/olvidar":
        return "Usá /olvidar todo para borrar el perfil completo."
    if command == "/limpiar":
        if callable(getattr(memory_clear, "clear", None)):
            memory_clear.clear()  # type: ignore[union-attr]
        return "Historial local borrado."
    return "Comando desconocido. Disponibles: " + ", ".join(COMMANDS)
