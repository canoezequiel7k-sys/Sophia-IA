from __future__ import annotations

COMMANDS = (
    "/ayuda", "/mute", "/unmute", "/silenciar", "/activarvoz",
    "/callate", "/perfil", "/olvidar", "/limpiar",     "/señalar reloj", "/señalar ventana", "/pantalla",
)


def handle_command(message: str, memory_clear: object | None = None) -> str | None:
    """Interpreta comandos locales; devuelve None si el texto debe ir a Gemini."""
    stripped = message.strip()
    if not stripped.startswith("/"):
        return None
    command = stripped.split(maxsplit=1)[0].lower()
    if command == "/ayuda":
        return "Comandos disponibles: " + ", ".join(COMMANDS)
    if command == "/mute" or command == "/silenciar":
        return "Voz silenciada. Usá /unmute o /activarvoz para volver a escucharme."
    if command == "/unmute" or command == "/activarvoz":
        return "Voz activada. Ya puedo hablarte de nuevo."
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
    if command == "/pantalla":
        return "PANTALLA_CONFIRMAR"
    if command == "/señalar":
        argumento = stripped[len(command):].strip().lower()
        if argumento in ("reloj", "tray", "bandeja"):
            return "SEÑALAR:CLOCK|RELOJ"
        if argumento in ("ventana", "active_window", "ventana-activa"):
            return "SEÑALAR:ACTIVE_WINDOW|VENTANA ACTIVA"
        return "Indicá /señalar reloj o /señalar ventana."
    return "Comando desconocido. Disponibles: " + ", ".join(COMMANDS)
