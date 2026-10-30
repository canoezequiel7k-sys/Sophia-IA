from __future__ import annotations

COMMANDS = (
    "/help",
    "/mute voice",
    "/mute sound",
    "/unmute voice",
    "/unmute sound",
    "/profile",
    "/forget",
    "/clear",
    "/point clock",
    "/point window",
    "/screen",
    "/exit",
)


def handle_command(message: str, memory_clear: object | None = None) -> str | None:
    """Interpreta comandos locales; devuelve None si el texto debe ir a Gemini."""
    stripped = message.strip()
    if not stripped.startswith("/"):
        return None
    command = stripped.split(maxsplit=1)[0].lower()
    argument = stripped[len(command):].strip().lower()
    if command == "/help" or command == "/ayuda":
        return "Available commands: " + ", ".join(COMMANDS)
    if command == "/mute":
        return "MUTE_VOICE" if argument in ("", "voice") else "MUTE_SOUND" if argument == "sound" else "Unknown mute option."
    if command == "/unmute":
        return "UNMUTE_VOICE" if argument in ("", "voice") else "UNMUTE_SOUND" if argument == "sound" else "Unknown unmute option."
    if command == "/profile":
        return "Local profile available; no personal profile is configured yet."
    if command == "/forget" or command == "/olvidar":
        return "Use /forget all to erase the complete profile." if argument != "all" else "PROFILE_CLEAR"
    if command == "/clear" or command == "/limpiar":
        if callable(getattr(memory_clear, "clear", None)):
            memory_clear.clear()  # type: ignore[union-attr]
        return "Conversation history cleared."
    if command == "/screen" or command == "/pantalla":
        return "PANTALLA_CONFIRMAR"
    if command == "/point":
        if argument in ("clock", "tray", "reloj"):
            return "SEÑALAR:CLOCK|CLOCK"
        if argument in ("window", "active_window", "ventana"):
            return "SEÑALAR:ACTIVE_WINDOW|ACTIVE WINDOW"
        return "Use /point clock or /point window."
    if command == "/exit":
        return "EXIT_SOPHIA"

    # Legacy aliases remain accepted for existing conversations.
    if command == "/silenciar":
        return "MUTE_VOICE"
    if command == "/activarvoz" or command == "/unmutevoice":
        return "UNMUTE_VOICE"
    if command == "/callate":
        return "MUTE_VOICE"
    if command == "/perfil":
        return "Local profile available; no personal profile is configured yet."
    if command == "/señalar":
        if argument in ("reloj", "clock", "tray", "bandeja"):
            return "SEÑALAR:CLOCK|CLOCK"
        if argument in ("ventana", "window", "active_window"):
            return "SEÑALAR:ACTIVE_WINDOW|ACTIVE WINDOW"
        return "Use /point clock or /point window."
    return "Unknown command. Available commands: " + ", ".join(COMMANDS)
